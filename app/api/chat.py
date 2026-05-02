import asyncio

from pydantic import ValidationError
from fastapi import (
    WebSocket,
    WebSocketDisconnect,  # noqa
    WebSocketException,  # noqa
    APIRouter,
    status,  # noqa
)

from app.utils.chat import ws_manager
from app.schemas.chat import ChatMessage, MessageType


chat_router = APIRouter()


@chat_router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    queue = asyncio.Queue()
    await ws_manager.register(websocket, queue)

    async def read_loop():
        """
        Read messages from the WebSocket & add them to the queue for processing.
        """
        async for data in websocket.iter_json():
            try:
                message = ChatMessage.model_validate(data)
            except ValidationError as ex:
                await queue.put(
                    {"error": "Invalid message format", "details": ex.errors()}
                )
                continue

            match message.type:
                case MessageType.JOIN_ROOM:
                    if not await ws_manager.is_joined(websocket, message.room):
                        await ws_manager.join_room(websocket, message.room)
                        await queue.put(
                            {
                                "message": f"{message.username} joined room {message.room}"
                            }
                        )
                        print(f"{message.username} joined room {message.room}")
                    else:
                        await queue.put({"error": "Already joined room"})

                case MessageType.LEAVE_ROOM:
                    if await ws_manager.is_joined(websocket, message.room):
                        await ws_manager.leave_room(websocket, message.room)
                        await queue.put(
                            {"message": f"{message.username} left room {message.room}"}
                        )
                        print(f"{message.username} left room {message.room}")
                    else:
                        await queue.put({"error": "Not in room, Please join first"})

                case MessageType.CHAT_MESSAGE:
                    if not await ws_manager.is_joined(websocket, message.room):
                        await queue.put({"error": "Not in room, Please join first"})
                    else:
                        await ws_manager.broadcast(
                            message.content, message.room, message.username
                        )
                        print(
                            f"{message.username} in {message.room}: {message.content}"
                        )

                # case _:
                #     raise WebSocketException(
                #         code=status.HTTP_400_BAD_REQUEST, reason="Invalid message type"
                #     )

    async def write_loop():
        """
        Listen for messages in the queue and send them to the WebSocket.
        """
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)

    read_task = asyncio.create_task(read_loop())
    write_task = asyncio.create_task(write_loop())

    done, pending = await asyncio.wait(
        [read_task, write_task],
        return_when=asyncio.FIRST_EXCEPTION,
    )

    for task in pending:
        task.cancel()

    await ws_manager.disconnect(websocket)
