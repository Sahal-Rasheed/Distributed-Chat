import asyncio

from fastapi import WebSocket

lock = asyncio.Lock()


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[asyncio.Queue]] = {}
        self.ws_to_queue: dict[WebSocket, asyncio.Queue] = {}

    async def register(self, websocket: WebSocket, queue: asyncio.Queue):
        async with lock:
            self.ws_to_queue[websocket] = queue

    async def join_room(self, websocket: WebSocket, room: str):
        async with lock:
            queue = self.ws_to_queue[websocket]

            if room not in self.active_connections:
                self.active_connections[room] = []

            self.active_connections[room].append(queue)

        # dont send this message inside the lock,
        # to avoid blocking other operations while sending message
        # await websocket.send_json({"message": f"Joined room {room}"})

    async def leave_room(self, websocket: WebSocket, room: str):
        async with lock:
            queue = self.ws_to_queue.get(websocket)

            if (
                room in self.active_connections
                and queue in self.active_connections[room]
            ):
                self.active_connections[room].remove(queue)

        # dont send this message inside the lock,
        # to avoid blocking other operations while sending message
        # await websocket.send_json({"message": f"Left room {room}"})

    async def broadcast(self, message: str, room: str, username: str):
        async with lock:
            # get a snapshot of current queues in the room for the current broadcast,
            # we will add messages to these queues outside the lock, 
            # to avoid blocking other operations while adding messages to queues as its a I/O operation (await)
            queues = list(self.active_connections.get(room, []))

        for q in queues:
            await q.put({"message": message, "username": username})

    async def disconnect(self, websocket: WebSocket):
        async with lock:
            queue = self.ws_to_queue.pop(websocket, None)
            if not queue:
                return

            rooms_to_delete = []

            for room, queues in self.active_connections.items():
                if queue in queues:
                    queues.remove(queue)
                    if not queues:
                        rooms_to_delete.append(room)

            for room in rooms_to_delete:
                del self.active_connections[room]

    async def is_joined(self, websocket: WebSocket, room: str) -> bool:
        async with lock:
            queue = self.ws_to_queue.get(websocket)
            return (
                room in self.active_connections
                and queue in self.active_connections[room]
            )


ws_manager = WebSocketConnectionManager()
