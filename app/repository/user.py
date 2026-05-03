from sqlalchemy import select
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.user import UserCreate
from app.repository.base import BaseRepository


class UserRepository(BaseRepository[User]):
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(self.model).where(self.model.email == email))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, obj_in: UserCreate) -> User:
        from app.services.auth import auth_service

        create_data = obj_in.model_dump(exclude={"password"})
        db_obj = User(**create_data)
        db_obj.password = auth_service.hash_password(obj_in.password)
        try:
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except IntegrityError as err:
            await db.rollback()
            if "email" in str(err.orig):
                raise HTTPException(status_code=400, detail="Email already registered.")

            raise HTTPException(status_code=400, detail="User creation failed.")


user_repository = UserRepository(User)
