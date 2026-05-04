import json
import asyncio
from typing import TYPE_CHECKING

from redis.asyncio import ConnectionPool, Redis, ConnectionError  # noqa

from app.core.config import settings

if TYPE_CHECKING:
    from app.services.socket import WebSocketConnectionManager


class RedisPubSubManager:
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.subscribed_rooms: set = set()

    async def connect(self):
        """
        Initialize both connections for publishing and subscribing.
         - `redis_client` is used for publishing messages (normal redis client).
         - `pubsub` is used for subscribing to channels [rooms] (dedicated pubsub object).
        """
        # self.redis_client = Redis(
        #     connection_pool=ConnectionPool.from_url(settings.REDIS_URL),
        #     decode_responses=True,
        # )
        self.redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()

        # test connection
        if not await self.redis_client.ping():
            raise ConnectionError("Failed to connect to Redis Client")

    async def subscribe(self, room_id: str):
        """
        Subscribe to a Redis channel for the given room_id if not already subscribed.
         - we only subscribe once per room, even if multiple users join the same room.
        """
        channel_name = f"room:{room_id}"
        if channel_name not in self.subscribed_rooms:
            await self.pubsub.subscribe(channel_name)
            self.subscribed_rooms.add(channel_name)

    async def unsubscribe(self, room_id: str):
        """
        Unsubscribe from a Redis channel for the given room_id.
         - we only unsubscribe when the last user leaves the room.
        """
        channel_name = f"room:{room_id}"
        if channel_name in self.subscribed_rooms:
            await self.pubsub.unsubscribe(channel_name)
            self.subscribed_rooms.remove(channel_name)

    async def subscriber_coroutine(self, ws_manager: "WebSocketConnectionManager"):
        """
        Listens for messages from all subscribed channels and dispatches them to local WebSocket queues.
         - This runs in a background task and continuously listens for messages from Redis.
         - When a message is received, it looks up which users are in the corresponding room
           on this server instance and puts the message in their queues.
         - Message Example:
            {
                "type": "message",
                "channel": "room:abc",
                "data": "{\"sender\": \"user_A\", \"content\": \"Hello\"}"
            }
        """
        while True:
            try:
                if not self.subscribed_rooms:
                    await asyncio.sleep(1)
                    continue
                
                async for raw_message in self.pubsub.listen():
                    # skip subscribe/unsubscribe confirmations msges
                    if raw_message["type"] != "message":
                        continue

                    channel = raw_message["channel"]  # "room:abc"
                    room_id = channel.split(":")[1]  # "abc"

                    # look up who is in this room on this server instance
                    # and send the message to their queues
                    if room_id in ws_manager.active_connections:
                        queues = list(
                            ws_manager.active_connections[room_id]
                        )  # make snapshot to avoid issues if the data changes while iterating
                        try:
                            payload = json.loads(raw_message["data"])
                        except json.JSONDecodeError:
                            print(
                                f"Received invalid message from Redis: {raw_message['data']}"
                            )
                            continue
                        for user_queue in queues:
                            await user_queue.put(payload)

            except ConnectionError:
                print("Redis connection lost. Reconnecting...")
                await asyncio.sleep(2)  # back off before retrying
                await self.connect()

                # resub to all rooms
                for room in self.subscribed_rooms:
                    await self.pubsub.subscribe(room)
                continue
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                print(f"Error in Redis subscriber coroutine: {ex}")
                await asyncio.sleep(1)

    async def publish(self, room_id: str, message: str):
        """
        Publish a message to the Redis channel of the given room_id.
         - This will be called when a user sends a chat message, and it will broadcast to all subscribers of that room.
        """
        channel_name = f"room:{room_id}"
        await self.redis_client.publish(channel_name, message)

    async def close(self):
        """
        Clean up Redis connections when the application shuts down.
        """
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()


redis_manager = RedisPubSubManager()
