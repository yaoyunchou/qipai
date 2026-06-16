from pydantic import BaseModel, Field

from app.models.user import UserRole


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: UserRole
    is_enabled: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=64)
    display_name: str = Field(default="", max_length=64)
    role: UserRole


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    role: UserRole | None = None
    is_enabled: bool | None = None
    password: str | None = Field(default=None, min_length=4, max_length=64)
