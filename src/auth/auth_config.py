from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (AuthenticationBackend,
                                          CookieTransport, JWTStrategy)
from src.config import settings

cookie_transport = CookieTransport(cookie_name="user_cookie", cookie_max_age=3600)

# JWTStrategy соответствует протоколу для стратегий аутентификации в FastAPI Users.
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.secret, lifetime_seconds=3600)

# Комбинация транспорта аутентификации и стратегии.
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
from src.auth.manager import get_user_manager
from src.auth.models import User

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# Создание dependency для получения текущего пользователя
# Используется как dependency в маршрутах, например:
# @router.get("/protected-route")
# async def protected_route(user: User = Depends(current_user)):
current_user = fastapi_users.current_user()
