import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.services.socket import ws_manager
from app.services.redis import redis_manager
from app.api.router import router as api_router
from app.db.async_session import init_models, async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    https://fastapi.tiangolo.com/advanced/events/
    """
    await init_models()
    print("Database models initialized")

    await redis_manager.connect()
    print("Connected to Redis")

    # start the redis subscriber coroutine in the bg.
    subscriber_task = asyncio.create_task(
        redis_manager.subscriber_coroutine(ws_manager)
    )
    print("Started Redis subscriber coroutine")

    yield

    await async_engine.dispose()
    print("Database engine disposed")

    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass
    finally:
        print("Redis subscriber coroutine closed")

    await redis_manager.close()
    print("Redis connections closed")


app = FastAPI(
    debug=settings.DEBUG,
    title=settings.PROJECT_NAME,
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/")
async def root():
    print("Root endpoint accessed")
    return {"message": "Welcome to the Distributed Chat App!"}


app.include_router(api_router)
