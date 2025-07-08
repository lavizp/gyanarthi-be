from typing import List
from bson import ObjectId
from fastapi import APIRouter, Depends,Request, Response, HTTPException,File,UploadFile
from app.db.mongo import get_db
from app.schemas.research import Research, ResearchCreate
from app.schemas.written_article import WrittenArticle
from app.schemas.uploaded_article import UploadedArticle
import cloudinary.uploader
from app.config import cloudinary
router = APIRouter(prefix='/research')
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import fitz  
import tempfile
import requests
import os

@router.post("")
async def createResearch(payload: ResearchCreate, req: Request, res: Response, db=Depends(get_db)):
    user_id = req.state.user["id"]
    data = payload.model_dump()

    pdf_url = data["pdf_url"]  # make sure frontend sends this
    if not pdf_url:
        raise HTTPException(status_code=400, detail="pdf_url is required")

    # Download PDF
    pdf_response = requests.get(pdf_url)
    if pdf_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Unable to download PDF")

    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_response.content)
        pdf_path = tmp.name

    
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(full_text)
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectordb = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    docs = [{"page_content": c, "metadata": {"user_id": str(user_id)}} for c in chunks]
    vectordb.add_texts(texts=[d["page_content"] for d in docs], metadatas=[d["metadata"] for d in docs])
    embedding_ids = [str(i) for i in range(len(docs))]  

    
    new_research = Research(
        user_id=ObjectId(str(user_id)),
        description=data["description"],
        title=data["title"]
    )
    insert_result = await db["research"].insert_one(new_research.model_dump(by_alias=True))
    research_id = insert_result.inserted_id

    new_article = UploadedArticle(
        user_id=str(user_id),
        research_id=str(research_id),
        original_text=full_text,
        chunks=chunks,
        embedding_ids=embedding_ids,
    )
    inserted_article = await db["uploaded_article"].insert_one(new_article.model_dump(by_alias=True))

    new_written_article = WrittenArticle(
        user_id=ObjectId(str(user_id)),
        research_id=str(research_id),
        title=data["title"],
        content="",
        ai_feedback=None
    )
    await db["written_article"].insert_one(new_written_article.model_dump(by_alias=True))

    os.remove(pdf_path)

    return {
        "message": "Research created and embedded",
        "research": new_research,
        "uploaded_article_id": inserted_article.inserted_id,
        "written_article": new_written_article
    }

@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...), db=Depends(get_db)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDFs are allowed")
    
    try:
        result = cloudinary.uploader.upload(file.file, resource_type="raw")
        return {"url": result["secure_url"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[Research],response_model_by_alias=False)
async def getAlResearch(req: Request, db=Depends(get_db)):
    user_id = req.state.user["id"]
    cursor = db["research"].find({"user_id": ObjectId(str(user_id))})
    research_list = await cursor.to_list(length=None)
    return [Research(**r) for r in research_list]

@router.post("/generate")
async def generateArticle(req: Request, db = Depends(get_db)):
    user_id = req.state.user["id"]
    