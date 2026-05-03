from fastapi import APIRouter

from app.api.http import auth
from app.api.http import user
from app.api.http import chat
from app.core.config import settings
from app.api.ws import chat as ws_chat

router = APIRouter()

# HTTP
router.include_router(
    auth.auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"]
)
router.include_router(
    user.user_router, prefix=f"{settings.API_V1_STR}/users", tags=["users"]
)
router.include_router(
    chat.chat_router, prefix=f"{settings.API_V1_STR}/chats", tags=["chat"]
)

# WS
router.include_router(ws_chat.chat_ws_router, prefix="/ws", tags=["webSockets"])
