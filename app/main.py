import logging
from contextlib import asynccontextmanager  # noqa

from fastapi import FastAPI

from app.api import router as api_router

logger = logging.getLogger(__name__)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """
#     https://fastapi.tiangolo.com/advanced/events/
#     """
#     await init_models()
#     logger.info("Database models initialized")
#     redis_client.connect()
#     logger.info("Connected to Redis")

#     yield

#     await async_engine.dispose()
#     logger.info("Database engine disposed")
#     redis_client.close()
#     logger.info("Disconnected from Redis")


app = FastAPI()


@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Chat API!"}


app.include_router(api_router)
