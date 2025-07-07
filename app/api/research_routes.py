from typing import List
from bson import ObjectId
from fastapi import APIRouter, Depends,Request, Response, HTTPException,File,UploadFile
from app.db.mongo import get_db
from app.schemas.research import Research, ResearchCreate
from app.schemas.written_article import WrittenArticle
import cloudinary.uploader
from app.config import cloudinary
router = APIRouter(prefix='/research')

@router.post("")
async def createResearch(payload: ResearchCreate, req: Request,res: Response,db = Depends(get_db)):
    user_id = req.state.user["id"]
    data = payload.model_dump()
    new_research=Research (
       user_id=ObjectId(str(user_id)),
       description=data["description"],
       title=data["title"]
    )
    insert_result = await db["research"].insert_one(new_research.model_dump(by_alias=True))
    research_id = insert_result.inserted_id

    new_written_article = WrittenArticle(
        user_id=ObjectId(str(user_id)),
        research_id=str(research_id), 
        title=data["title"],
        content="",  
        ai_feedback=None,
    )
    await db["written_article"].insert_one(new_written_article.model_dump(by_alias=True))
    return {"message": "Research created", "research": new_research, "written_article": new_written_article}

@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
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
    