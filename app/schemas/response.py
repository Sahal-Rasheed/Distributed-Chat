from typing import Generic, TypeVar

from pydantic import BaseModel


DataT = TypeVar("DataT")


class StandardResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str = "Success"
    data: DataT | None = None
