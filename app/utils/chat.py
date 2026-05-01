import asyncio

from fastapi import WebSocket

lock = asyncio.Lock()


class WebSocketConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def join_room(self, websocket: WebSocket, room: str):
        async with lock:
            if room not in self.active_connections:
                self.active_connections[room] = []
            self.active_connections[room].append(websocket)
            await websocket.send_json({"message": f"Joined room {room}"})

    async def leave_room(self, websocket: WebSocket, room: str):
        async with lock:
            if room in self.active_connections:
                self.active_connections[room].remove(websocket)
                await websocket.send_json({"message": f"Left room {room}"})

    async def broadcast(self, message: str, room: str, username: str):
        if room in self.active_connections:
            for connection in self.active_connections[room]:
                await connection.send_json({"message": message, "username": username})

        print(f"Active connections: {self.active_connections}")

    async def disconnect(self, websocket: WebSocket):
        async with lock:
            for room, connections in self.active_connections.items():
                if websocket in connections:
                    connections.remove(websocket)
                    if not connections:
                        del self.active_connections[room]
                    break

    async def is_joined(self, websocket: WebSocket, room: str) -> bool:
        async with lock:
            return (
                room in self.active_connections
                and websocket in self.active_connections[room]
            )


ws_manager = WebSocketConnectionManager()
