from typing import List

import cloudinary.uploader
from bson import ObjectId
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)

from app.config import cloudinary
from app.db.mongo import get_db
from app.schemas.research import (
    GenerateArticle,
    GenerateFullArticle,
    Research,
    ResearchCreate,
)
from app.schemas.uploaded_article import UploadedArticle
from app.schemas.written_article import WrittenArticle, WrittenArticleUpdate
from app.storages.rag_system import RAGSystem

router = APIRouter(prefix="/research")
import os
import tempfile

import requests
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma


@router.post("")
async def createResearch(
    payload: ResearchCreate, req: Request, res: Response, db=Depends(get_db)
):
    user_id = req.state.user["id"]
    data = payload.model_dump()
    rag_system = RAGSystem()
    pdf_urls = data["pdf_url"]

    if not pdf_urls or len(pdf_urls) == 0:
        raise HTTPException(status_code=400, detail="At least one pdf_url is required")

    # Create the research document first
    new_research = Research(
        user_id=ObjectId(str(user_id)),
        description=data["description"],
        title=data["title"],
        date=data["date"],
    )
    insert_result = await db["research"].insert_one(
        new_research.model_dump(by_alias=True)
    )
    research_id = insert_result.inserted_id

    uploaded_articles = []
    temp_files = []
    failed_pdfs = []

    try:
        # Process each PDF
        for idx, pdf_url in enumerate(pdf_urls):
            try:
                # Download PDF
                pdf_response = requests.get(pdf_url, timeout=30)
                if pdf_response.status_code != 200:
                    failed_pdfs.append(
                        {"url": pdf_url, "error": f"HTTP {pdf_response.status_code}"}
                    )
                    continue

                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_response.content)
                    pdf_path = tmp.name
                    temp_files.append(pdf_path)

                # Extract text from PDF
                full_text = rag_system.get_full_text(pdf_path=pdf_path)

                # Validate that we have text
                if not full_text or len(full_text.strip()) == 0:
                    failed_pdfs.append(
                        {"url": pdf_url, "error": "No text could be extracted from PDF"}
                    )
                    continue

                # Create chunks
                chunks = rag_system.get_chunks(full_text=full_text)

                # Validate chunks
                if not chunks or len(chunks) == 0:
                    failed_pdfs.append(
                        {"url": pdf_url, "error": "No chunks created from PDF text"}
                    )
                    continue

                # Create embeddings
                embedding_ids = rag_system.get_document_embeddings(
                    chunks=chunks, user_id=user_id, research_id=research_id
                )

                # Validate embeddings
                if not embedding_ids or len(embedding_ids) == 0:
                    failed_pdfs.append(
                        {"url": pdf_url, "error": "Failed to create embeddings"}
                    )
                    continue

                # Create uploaded article document
                new_article = UploadedArticle(
                    user_id=str(user_id),
                    research_id=str(research_id),
                    original_text=full_text,
                    chunks=chunks,
                    embedding_ids=embedding_ids,
                )
                inserted_article = await db["uploaded_article"].insert_one(
                    new_article.model_dump(by_alias=True)
                )

                uploaded_articles.append(
                    {
                        "id": str(inserted_article.inserted_id),
                        "pdf_url": pdf_url,
                        "chunks_count": len(chunks),
                        "embeddings_count": len(embedding_ids),
                    }
                )

            except Exception as e:
                failed_pdfs.append({"url": pdf_url, "error": str(e)})
                print(f"Error processing PDF {pdf_url}: {e}")

        # Check if at least one PDF was successfully processed
        if len(uploaded_articles) == 0:
            # Rollback: delete the research document
            await db["research"].delete_one({"_id": research_id})
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Failed to process any PDFs",
                    "failed_pdfs": failed_pdfs,
                },
            )

        # Create written article (only one per research)
        new_written_article = WrittenArticle(
            user_id=ObjectId(str(user_id)),
            research_id=str(research_id),
            title=data["title"],
            content="",
            ai_feedback=None,
        )
        written_article_result = await db["written_article"].insert_one(
            new_written_article.model_dump(by_alias=True)
        )

    finally:
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"Error removing temp file {temp_file}: {e}")

    response_data = {
        "message": f"Research created with {len(uploaded_articles)} PDF(s) successfully processed",
        "research": new_research,
        "uploaded_articles": uploaded_articles,
        "written_article_id": str(written_article_result.inserted_id),
    }

    # Include failed PDFs info if any
    if failed_pdfs:
        response_data["failed_pdfs"] = failed_pdfs
        response_data["message"] += f" ({len(failed_pdfs)} PDF(s) failed)"

    return response_data


@router.put(
    "/written_article/{id}",
    response_model=WrittenArticle,
    response_model_by_alias=False,
)
async def update_written_article(
    id: str,
    payload: WrittenArticleUpdate = Body(...),
    req: Request = None,
    db=Depends(get_db),
):
    user_id = req.state.user["id"]

    article = await db["written_article"].find_one(
        {"research_id": id, "user_id": ObjectId(str(user_id))}
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    update_doc = {}
    if payload.title is not None:
        update_doc["title"] = payload.title
    if payload.content is not None:
        update_doc["content"] = payload.content

    if not update_doc:
        raise HTTPException(status_code=400, detail="Nothing to update")

    await db["written_article"].update_one({"research_id": id}, {"$set": update_doc})

    updated = await db["written_article"].find_one({"research_id": id})
    return WrittenArticle(**updated)


@router.post(
    "/written_article/{id}/review",
    response_model=WrittenArticle,
    response_model_by_alias=False,
)
async def review_written_article(id: str, req: Request, db=Depends(get_db)):
    user_id = req.state.user["id"]
    print(id)
    print(user_id)
    article = await db["written_article"].find_one(
        {"research_id": id, "user_id": ObjectId(str(user_id))}
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    content = article.get("content") or ""
    if not content.strip():
        raise HTTPException(
            status_code=400, detail="Article content is empty; nothing to review"
        )

    # Generate feedback (use your RAGSystem, or LLM of choice)
    rag_system = RAGSystem()
    try:
        feedback = await rag_system.review_article(
            title=article.get("title", ""),
            content=content,
            research_id=article.get(
                "research_id"
            ),  # optional, if you want to cross-check against sources
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate review: {str(e)}"
        )
    print(feedback.get("grammar_score"))
    ai_feedback_doc = {
        "grammar_score": feedback.get("grammar_score"),
        "clarity_score": feedback.get("clarity_score"),
        "factual_correctness": feedback.get("factual_correctness"),
        "suggestions": feedback.get("suggestions"),
    }

    # Persist feedback
    await db["written_article"].update_one(
        {"research_id": id}, {"$set": {"ai_feedback": ai_feedback_doc}}
    )

    updated = await db["written_article"].find_one({"research_id": id})
    return WrittenArticle(**updated)


@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), db=Depends(get_db)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDFs are allowed")
    try:
        result = cloudinary.uploader.upload(file.file, resource_type="raw")
        return {"url": result["secure_url"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[Research], response_model_by_alias=False)
async def getAlResearch(req: Request, db=Depends(get_db)):
    user_id = req.state.user["id"]
    cursor = db["research"].find({"user_id": ObjectId(str(user_id))})
    research_list = await cursor.to_list(length=None)
    return [Research(**r) for r in research_list]


@router.get("/{id}", response_model=Research, response_model_by_alias=False)
async def get_research(id: str, req: Request, db=Depends(get_db)):
    user_id = req.state.user["id"]
    research = await db["research"].find_one(
        {"_id": ObjectId(id), "user_id": ObjectId(str(user_id))}
    )
    if not research:
        raise HTTPException(status_code=404, detail="Research not found")
    return Research(**research)


@router.get(
    "/written_article/{id}",
    response_model=WrittenArticle,
    response_model_by_alias=False,
)
async def get_article_detail(id: str, req: Request, db=Depends(get_db)):
    user_id = req.state.user["id"]
    article = await db["written_article"].find_one(
        {"research_id": id, "user_id": ObjectId(str(user_id))}
    )
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return WrittenArticle(**article)


@router.post("/generate")
async def generateArticle(payload: GenerateArticle, req: Request, db=Depends(get_db)):
    data = payload.model_dump()
    rag_system = RAGSystem()
    research_id = data["research_id"]
    query = data["query"]
    answer = rag_system.generate_answer(research_id=research_id, query=query)
    return answer


@router.post("/generate/full")
async def generateFullArticle(
    payload: GenerateFullArticle, req: Request, db=Depends(get_db)
):
    data = payload.model_dump()
    rag_system = RAGSystem()
    research_id = data["research_id"]
    query = data["query"]
    answer = rag_system.generate_answer(research_id=research_id, query=query)
    return answer
