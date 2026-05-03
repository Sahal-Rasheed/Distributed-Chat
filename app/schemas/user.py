from uuid import UUID

from pydantic import BaseModel, EmailStr, StrictStr, ConfigDict


class UserBase(BaseModel):
    """Base schema for User model."""

    name: StrictStr | None = None
    email: EmailStr | None = None


class UserCreate(UserBase):
    """Schema for new User registration with required fields."""

    name: StrictStr
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    """Schema for updating existing User information."""

    ...


class UserInDBBase(UserBase):
    """Base schema for database User representation with ID."""

    id: UUID

    # deprecated
    # class Config:
    # from_attributes = True

    # pydantic v2
    # model_config = {
    #     "from_attributes": True,
    # }

    # or
    model_config = ConfigDict(from_attributes=True)


class UserPublic(UserInDBBase):
    """Public User schema for API responses."""

    ...


class Token(BaseModel):
    """Schema for JWT token."""

    access_token: str
    token_type: str
