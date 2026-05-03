from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.base import Base
from app.core.config import settings


async_engine = create_async_engine(
    settings.POSTGRES_DATABASE_URL, echo=False, future=True
)

async_session_maker = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
#     async with async_session_maker() as session:
#         try:
#             yield session
#         except Exception:
#             await session.rollback()
#             raise
#         finally:
#             await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_scope() as session:
        yield session


async def init_models() -> None:
    async with async_engine.begin() as conn:
        # uncomment below line to drop all tables before creating them
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


# Quick note on DB session architecture:
# - For HTTP endpoints: Use the `get_async_session` dependency. FastAPI creates
#   and closes the session cleanly per request.
# - For WS endpoints: Use the `session_scope` context manager manually inside
#   the message loop. `session_scope` can be used independently to get a session
#
# Why separate them?
# 1. If we use `Depends()` in a WS endpoint, the session stays alive for the
#    entire WebSocket connection. This is dangerous (stale data, memory leaks).
#    We want a fresh session per *message*, closed immediately after processing.
# 2. We cannot use `@asynccontextmanager` (session_scope) directly as a FastAPI
#    dependency because FastAPI expects a raw generator function, not a context
#    manager object.
#
# Solution:
# - `session_scope`: Core context manager for WS/manual use.
# - `get_async_session`: A raw generator that unwraps `session_scope` purely
#   so FastAPI's dependency injection system can use it for HTTP endpoints,
#   as now its signature matches what FastAPI expects.
