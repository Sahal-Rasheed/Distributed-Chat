from enum import StrEnum
from pydantic import BaseModel


class MessageType(StrEnum):
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    CHAT_MESSAGE = "chat_message"


class ChatMessage(BaseModel):
    type: MessageType
    room: str
    username: str | None = None
    content: str | None = None
