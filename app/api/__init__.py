from fastapi import APIRouter

from app.api.chat import chat_router


router = APIRouter()
router.include_router(chat_router, prefix="/ws", tags=["chats"])
