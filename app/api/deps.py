from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, Query, HTTPException, WebSocketException, status

from app.models import User
from app.core.config import settings
from app.services.auth import auth_service
from app.repository.user import user_repository
from app.db.async_session import get_async_session

# db dependency
DBSessionDep = Annotated[AsyncSession, Depends(get_async_session)]

# token dependency (Authorize -> Basic Auth -> Token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")
TokenDep = Annotated[str, Depends(oauth2_scheme)]

# current user dependency (for http endpoints)
async def get_current_user(token: TokenDep, db: DBSessionDep) -> User:
    print(f"Token: {token}")
    email = auth_service.get_email_from_token(token)
    user = await user_repository.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

CurrentUserDep = Annotated[User, Depends(get_current_user)]


# current ws user dependency (for ws endpoints)
async def get_current_ws_user(db: DBSessionDep, token: str = Query(...)) -> User:
    print(f"WS Token: {token}")
    email = auth_service.get_email_from_token(token)
    user = await user_repository.get_by_email(db, email=email)
    if not user:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Could not validate credentials",
        )
    return user

CurrentWSUserDep = Annotated[User, Depends(get_current_ws_user)]
