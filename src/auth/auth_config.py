from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (AuthenticationBackend,
                                          CookieTransport, JWTStrategy)
from src.config import settings

from fastapi import Request

# Транспорт для access токена
cookie_transport = CookieTransport(
    cookie_name="access_token",
    cookie_max_age=settings.access_exp,
    cookie_secure=True,  # Только для HTTPS
    cookie_httponly=True  # Защита от XSS
)

# Транспорт для refresh токена
refresh_cookie_transport = CookieTransport(
    cookie_name="refresh_token",
    cookie_max_age=settings.refresh_exp,
    cookie_secure=True,
    cookie_httponly=True,
    cookie_samesite="strict"  # Защита от CSRF
)

# Стратегия аутентификации для access токена (короткоживущий)
def get_access_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.access_secret,
        lifetime_seconds=settings.access_exp,
        algorithm=settings.algorithm
    )

# Стратегия аутентификации для refresh токена (долгоживущий)
def get_refresh_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.refresh_secret,
        lifetime_seconds=settings.refresh_exp,
        algorithm=settings.algorithm
    )

auth_backend = AuthenticationBackend(
    name="access_jwt",
    transport=cookie_transport,
    get_strategy=get_access_strategy,
)

refresh_backend = AuthenticationBackend(
    name="refresh_jwt",
    transport=refresh_cookie_transport,
    get_strategy=get_refresh_strategy,
)

async def get_enabled_backends(request: Request):
    path = request.url.path
    if any(path.endswith(p) for p in ["/refresh", "/access-token", "/logout"]):
        return [refresh_backend]
    return [auth_backend]


from src.auth.manager import get_user_manager
from src.auth.models import User

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend, refresh_backend],
)

# Создание dependency для получения текущего пользователя
# Используется как dependency в защищенных маршрутах, например:
# @router.get("/protected-route")
# async def protected_route(user: User = Depends(current_user)):

# Dependency для получения текущего пользователя
current_user = fastapi_users.current_user(active=True, get_enabled_backends=get_enabled_backends)
