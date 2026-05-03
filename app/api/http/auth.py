from typing import Annotated, Any

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.user import Token
from app.api.deps import DBSessionDep
from app.services.auth import auth_service


auth_router = APIRouter()


@auth_router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(
    db: DBSessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Any:
    """JWT login endpoint"""
    user = await auth_service.authenticate(
        db=db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # OAuth2[ OAuth2PasswordBearer ] compatibility Response
    return {
        "access_token": auth_service.create_access_token(
            user_id=user.id, user_email=user.email
        ),
        "token_type": "bearer",
    }
