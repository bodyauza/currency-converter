from typing import Optional

from fastapi_users import schemas
from pydantic import BaseModel

# Модели Pydantic для автоматической валидации получаемых данных (DTO).

class UserRead(schemas.BaseUser[int]):
    id: int
    email: str
    username: str
    role_id: int
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

    class Config:
        from_attributes = True


class UserCreate(schemas.BaseUserCreate):
    username: str
    email: str
    password: str
    role_id: int
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False

# Модель для возврата пары токенов
class TokenPair(BaseModel):
    access_token: str  # Краткосрочный токен доступа
    refresh_token: str  # Долгосрочный токен обновления
