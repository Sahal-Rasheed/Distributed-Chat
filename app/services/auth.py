from datetime import datetime, timedelta, UTC

import jwt
from pwdlib import PasswordHash
from pydantic import ValidationError
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status

from app.models import User
from app.core.config import settings
from app.repository.user import user_repository


class AuthException(BaseException):
    pass


class AuthService:
    """JWT Authentication Service Class"""

    def __init__(self):
        self.password_hash = PasswordHash.recommended()
        self.SECRET_KEY = settings.JWT_SECRET
        self.ALGORITHM = settings.ALGORITHM

    def hash_password(self, password: str) -> str:
        return self.password_hash.hash(password)

    def verify_password(self, plan_pw: str, hashed_pw: str) -> bool:
        return self.password_hash.verify(plan_pw, hashed_pw)

    def create_access_token(
        self,
        user_id: int,
        user_email: str,
    ) -> str:
        payload = {
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int(
                (
                    datetime.now(UTC)
                    + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                ).timestamp()
            ),
            "sub": str(user_id),
            "email": user_email,
        }
        access_token = jwt.encode(payload, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return access_token

    def get_email_from_token(self, token: str) -> str | HTTPException:
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            email = payload.get("email")
            return email
        except (jwt.PyJWTError, ValidationError, InvalidTokenError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate token credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def authenticate(
        self, db: AsyncSession, email: str, password: str
    ) -> User | None:
        user = await user_repository.get_by_email(db, email)
        if not user:
            return None
        if not self.verify_password(password, user.password):
            return None
        return user


auth_service = AuthService()
