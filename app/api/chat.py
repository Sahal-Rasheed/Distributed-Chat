from pydantic import ValidationError
from fastapi import (
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    APIRouter,
    status,
)

from app.utils.chat import ws_manager
from app.schemas.chat import ChatMessage, MessageType


chat_router = APIRouter()


@chat_router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        async for data in websocket.iter_json():
            try:
                message = ChatMessage.model_validate(data)
            except ValidationError as ex:
                await websocket.send_json(
                    {"error": "Invalid message format", "details": ex.errors()}
                )
                continue

            match message.type:
                case MessageType.JOIN_ROOM:
                    if not await ws_manager.is_joined(websocket, message.room):
                        await ws_manager.join_room(websocket, message.room)
                        print(f"{message.username} joined room {message.room}")
                    else:
                        await websocket.send_json({"error": "Already joined room"})

                case MessageType.LEAVE_ROOM:
                    if await ws_manager.is_joined(websocket, message.room):
                        await ws_manager.leave_room(websocket, message.room)
                        print(f"{message.username} left room {message.room}")
                    else:
                        await websocket.send_json(
                            {"error": "Not in room, Please join first"}
                        )

                case MessageType.CHAT_MESSAGE:
                    if not await ws_manager.is_joined(websocket, message.room):
                        await websocket.send_json(
                            {"error": "Not in room, Please join first"}
                        )
                    else:
                        print(
                            f"{message.username} in {message.room}: {message.content}"
                        )
                        await ws_manager.broadcast(message.content, message.room, message.username)

                case _:
                    raise WebSocketException(
                        code=status.HTTP_400_BAD_REQUEST, reason="Invalid message type"
                    )

    except WebSocketDisconnect as ex:
        print(f"WebSocket disconnected: {ex.reason}")
        await ws_manager.disconnect(websocket)

    finally:
        print("WebSocket connection closed")
