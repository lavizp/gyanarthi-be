from typing import List
from bson import ObjectId
from fastapi import APIRouter, Body, Depends,Request, Response, HTTPException
from app.schemas.chat import CreateChatRequest, ChatSessionModel, MessageModel,CreateMessageRequest
from app.db.mongo import get_db
from app.storages.rag_system import RAGSystem

router = APIRouter(prefix='/chat')

@router.post('/create')
async def create_new_chat(payload: CreateChatRequest, req: Request, res:Response, db= Depends(get_db)):
    user_id = req.state.user["id"]
    data = payload.model_dump()
    title = data['title']
    new_chat = ChatSessionModel(
        user_id=user_id,
        title=title
    )
    inserted_result = await db["chat"].insert_one(new_chat.model_dump(by_alias=True))
    chat_id = inserted_result.inserted_id
    return{
        "title":title,
        "id": str(chat_id)
    }

@router.get('/histories',response_model = List[ChatSessionModel])
async def get_all_chat_histories(req: Request, db = Depends(get_db)):
    user_id = req.state.user["id"]
    cursor = db["chat"].find({"user_id": ObjectId(str(user_id))}).sort("updated_at", -1)
    chat_list = await cursor.to_list(length=None)
    return [ChatSessionModel(**r) for r in chat_list]

@router.get("/history/{id}", response_model=List[MessageModel], response_model_by_alias=False)
async def get_messages_by_id(id: str, req: Request, db=Depends(get_db)):
    cursor = db["message"].find({"session_id": ObjectId(id)})
    messages = await cursor.to_list(length=None)  # convert cursor to list
    if not messages:
        raise HTTPException(status_code=404, detail="Message not found")
    return [MessageModel(**r) for r in messages]

@router.post('/stream', response_model=MessageModel)
async def stream_response(payload:CreateMessageRequest, req:Request, db=Depends(get_db)):
    rag_system = RAGSystem()
    # id= req.user["id"]
    data = payload.model_dump()
    user_message = data["content"]
    conversation_id = data["session_id"]

    new_message = MessageModel(
        session_id=ObjectId(conversation_id),
        content=user_message,
        role="user"
    )

    await db["message"].insert_one(new_message.model_dump(by_alias=False))

    history_cursor = db["message"].find({"session_id": ObjectId(conversation_id)}).sort("_id", 1)
    history_docs = await history_cursor.to_list(length=None)
    history = [f"{msg['role']}: {msg['content']}" for msg in history_docs]
    print('---------------------------')
    print(history)
    ai_response = rag_system.generate_chat_response(user_message, history)
    new_message = MessageModel(
        session_id=ObjectId(conversation_id),
        content=ai_response,
        role="assistant"
    )

    await db["message"].insert_one(new_message.model_dump(by_alias=False))

    return new_message

    
