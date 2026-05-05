import asyncio
from datetime import datetime, UTC

from pydantic import ValidationError
from fastapi import WebSocket, APIRouter

from app.api.deps import CurrentWSUserDep
from app.services.socket import ws_manager
from app.db.async_session import session_scope
from app.repository.chat import chat_message_repository
from app.schemas.chat import ChatMessage, MessageType, CreateChatMessage


chat_ws_router = APIRouter()


@chat_ws_router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket, user: CurrentWSUserDep):
    await websocket.accept()

    queue = asyncio.Queue()
    await ws_manager.register(websocket, queue)

    async def ping_loop():
        """
        Send periodic pings to the client to decide to keep the connection alive or not.
        """
        try:
            while True:
                await asyncio.sleep(30)  # ping every 30 seconds
                await queue.put({"type": "ping"})
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

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
                    joined = await ws_manager.join_room(websocket, message.room)
                    if joined:
                        await queue.put(
                            {
                                "message": f"{message.username} joined room {message.room}"
                            }
                        )
                        print(f"{message.username} joined room {message.room}")
                    else:
                        await queue.put({"error": "Already joined room"})

                case MessageType.LEAVE_ROOM:
                    left = await ws_manager.leave_room(websocket, message.room)
                    if left:
                        await queue.put(
                            {"message": f"{message.username} left room {message.room}"}
                        )
                        print(f"{message.username} left room {message.room}")
                    else:
                        await queue.put({"error": "Not in room, Please join first"})

                case MessageType.CHAT_MESSAGE:
                    sent = await ws_manager.broadcast(
                        websocket, message.content, message.room, message.username
                    )
                    if sent:
                        async with session_scope() as session:
                            await chat_message_repository.create(
                                db=session,
                                obj_in=CreateChatMessage(
                                    user_id=user.id,
                                    room=message.room,
                                    content=message.content,
                                    timestamp=datetime.now(UTC),
                                ),
                            )
                        print(
                            f"{message.username} in {message.room}: {message.content}"
                        )
                    else:
                        await queue.put({"error": "Not in room, Please join first"})

                case _:
                    await queue.put({"error": "Invalid message type"})

    async def write_loop():
        """
        Listen for messages in the queue and send them to the WebSocket.
        """
        try:
            while True:
                msg = await queue.get()
                await websocket.send_json(msg)
        except asyncio.CancelledError:
            raise
        except Exception:  # connection closed or cancelled
            pass

    ping_task = asyncio.create_task(ping_loop())
    read_task = asyncio.create_task(read_loop())
    write_task = asyncio.create_task(write_loop())

    # run both loops concurrently until one of them raises an exception (like WebSocketDisconnect) or disconnects normally
    done, pending = await asyncio.wait(
        [ping_task, read_task, write_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # on exception, .wait will return, we need to cancel the other task that is still running
    # .cancel() will send cancel signal to the task
    for task in pending:
        task.cancel()

    # waits until all those tasks actually finish cancelling,
    # this is important to ensure that all resources are cleaned up properly,
    # we cant just rely only on .cancel() because it just sends the cancellation signal
    await asyncio.gather(*pending, return_exceptions=True)

    await ws_manager.disconnect(websocket)
