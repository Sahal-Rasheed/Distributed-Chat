from typing import Any

from pydantic import TypeAdapter
from fastapi import APIRouter, status

from app.schemas.chat import ChatMessagesResponse
from app.schemas.response import StandardResponse
from app.api.deps import DBSessionDep, CurrentUserDep
from app.repository.chat import chat_message_repository


chat_router = APIRouter()


@chat_router.get(
    "/{room_id}/messages",
    response_model=StandardResponse[list[ChatMessagesResponse]],
    status_code=status.HTTP_200_OK,
)
async def list_chat_room_messages(
    db: DBSessionDep,
    _: CurrentUserDep,
    room_id: str,
    limit: int = 20,
    offset: int = 0,
) -> Any:
    """List messages in a chat room"""
    messages = await chat_message_repository.list_messages(
        db, room_id, limit=limit, offset=offset
    )
    # when returning a list of models via a generic response,
    # we will get a validation error, to fix this, (pydantic v2)
    # we can use a TypeAdapter to validate the list of models before returning the response
    return StandardResponse(
        data=TypeAdapter(list[ChatMessagesResponse]).validate_python(messages)
    )
