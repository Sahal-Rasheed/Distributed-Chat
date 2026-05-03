from uuid import UUID
from enum import StrEnum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageType(StrEnum):
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    CHAT_MESSAGE = "chat_message"


class ChatMessage(BaseModel):
    type: MessageType
    room: str
    username: str | None = None
    content: str | None = None


class CreateChatMessage(BaseModel):
    user_id: UUID
    room: str
    content: str
    timestamp: datetime


class ChatMessagesResponse(CreateChatMessage):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
