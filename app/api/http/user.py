from typing import Any

from fastapi import APIRouter, status

from app.repository.user import user_repository
from app.schemas.response import StandardResponse
from app.api.deps import DBSessionDep, CurrentUserDep
from app.schemas.user import UserCreate, UserUpdate, UserPublic


user_router = APIRouter()


@user_router.post(
    "/register",
    response_model=StandardResponse[UserPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(db: DBSessionDep, user_in: UserCreate) -> Any:
    """Register endpoint"""
    user = await user_repository.create(db=db, obj_in=user_in)
    return StandardResponse(
        message="User created successfully",
        data=user,
    )


@user_router.get(
    "/me", response_model=StandardResponse[UserPublic], status_code=status.HTTP_200_OK
)
async def read_user(current_user: CurrentUserDep) -> Any:
    """User read endpoint"""
    return StandardResponse(data=current_user)


@user_router.put(
    "/edit", response_model=StandardResponse[UserPublic], status_code=status.HTTP_200_OK
)
async def update_user(
    db: DBSessionDep, current_user: CurrentUserDep, user_in: UserUpdate
) -> Any:
    """User update endpoint"""
    user = await user_repository.update(db=db, id=current_user.id, obj_in=user_in)
    return StandardResponse(
        message="User updated successfully",
        data=user,
    )
