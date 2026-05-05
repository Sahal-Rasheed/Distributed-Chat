import json
import asyncio

from fastapi import WebSocket

from app.services.redis import redis_manager

lock = asyncio.Lock()


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[asyncio.Queue]] = {}
        self.ws_to_queue: dict[WebSocket, asyncio.Queue] = {}

    async def register(self, websocket: WebSocket, queue: asyncio.Queue):
        self.ws_to_queue[websocket] = queue
    
    async def get_room_queues(self, room: str) -> list[asyncio.Queue]:
        async with lock:
            return list(self.active_connections.get(room, []))

    async def join_room(self, websocket: WebSocket, room: str) -> bool:
        should_subscribe = False
        async with lock:
            queue = self.ws_to_queue[websocket]

            if room not in self.active_connections:
                self.active_connections[room] = []

            if queue in self.active_connections[room]:
                return False  # already joined

            # sub to redis channel for this room if not already subscribed
            should_subscribe = len(self.active_connections[room]) == 0
            self.active_connections[room].append(queue)

        # do the subscription outside the lock to avoid blocking other operations
        # since subscribing to a Redis channel is an I/O operation (await) and can take time
        if should_subscribe:
            await redis_manager.subscribe(room)

        return True

    async def leave_room(self, websocket: WebSocket, room: str) -> bool:
        should_unsubscribe = False
        async with lock:
            queue = self.ws_to_queue.get(websocket)
            if (
                room in self.active_connections
                and queue in self.active_connections[room]
            ):
                self.active_connections[room].remove(queue)
                # unsub from redis channel for this room if no one is in the room on this server instance
                if not self.active_connections[room]:
                    del self.active_connections[room]
                    should_unsubscribe = True
            else:
                return False  # not in room

        if should_unsubscribe:
            await redis_manager.unsubscribe(room)

        return True

    async def broadcast(
        self, websocket: WebSocket, message: str, room: str, username: str
    ) -> bool:
        async with lock:
            # get a snapshot of current queues in the room for the current broadcast,
            # we will add messages to these queues outside the lock,
            # to avoid blocking other operations while adding messages to queues as its a I/O operation (await)
            queue = self.ws_to_queue.get(websocket)

            if (
                room not in self.active_connections
                or queue not in self.active_connections[room]
            ):
                return False

            # queues = list(self.active_connections.get(room, []))

        # for q in queues:
        #     await q.put({"message": message, "username": username})

        # publish the message to the Redis channel corresponding to this room instead of sending to local queues
        # which will then be picked up by the `subscriber coroutine` and dispatched to all local queues of users
        # in that room on this server instance
        await redis_manager.publish(
            room_id=room,
            message=json.dumps({"message": message, "username": username}),
        )

        return True

    async def disconnect(self, websocket: WebSocket):
        rooms_to_unsubscribe = []
        async with lock:
            queue = self.ws_to_queue.pop(websocket, None)
            if not queue:
                return

            for room, queues in self.active_connections.items():
                if queue in queues:
                    queues.remove(queue)
                    if not queues:
                        rooms_to_unsubscribe.append(room)

            for room in rooms_to_unsubscribe:
                del self.active_connections[room]

        # redis i/o outside the lock
        for room in rooms_to_unsubscribe:
            await redis_manager.unsubscribe(room)


ws_manager = WebSocketConnectionManager()
