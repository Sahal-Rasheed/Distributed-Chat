from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage
from app.repository.base import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    async def list_messages(
        self, db: AsyncSession, room_id: str, limit: int = 100, offset: int = 0
    ) -> list[ChatMessage]:
        query = (
            select(self.model)
            .where(self.model.room == room_id)
            .offset(offset)
            .limit(limit)
            .order_by(self.model.timestamp.desc())
        )
        result = await db.execute(query)
        return result.scalars().all()


chat_message_repository = ChatMessageRepository(ChatMessage)
