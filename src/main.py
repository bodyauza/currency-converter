from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, Request, Form, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse
from sqlalchemy_utils import database_exists, create_database

from src.auth.manager import get_user_manager
from src.config import settings
from src.database import Base, engine, get_async_session
from src.auth.auth_config import fastapi_users, auth_backend, current_user, \
    refresh_backend, get_refresh_strategy, get_access_strategy
from src.auth.schemas import UserRead, UserCreate, TokenPair
from src.auth.models import User, Role

from fastapi import Response, status
from fastapi.responses import JSONResponse
from fastapi_users import models


templates = Jinja2Templates(directory="templates")

async def create_clients_db():
    print("До create_all:", Base.metadata.tables.keys())
    # Создаем временный синхронный движок для проверки/создания БД
    sync_url = engine.url.set(drivername="postgresql+psycopg2")  # меняем на синхронный драйвер
    sync_engine = create_engine(sync_url)

    if not database_exists(sync_engine.url):
        create_database(sync_engine.url)
    sync_engine.dispose()  # закрываем синхронное соединение
    try:
        async with engine.begin() as conn:
            # Синхронно создает все таблицы из моделей, наследующих Base
            await conn.run_sync(Base.metadata.create_all)
        print("Таблицы базы данных успешно созданы")
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")


# Инициализация FastAPI с lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_clients_db()
    yield

app = FastAPI(
    title='Currency Conversion',
    lifespan=lifespan
)


app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["Authentication"],
)


app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Authentication"],
)


origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    # port for react
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin",
                   "Authorization"],
)


# Добавляем новые маршруты для работы с токенами
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/refresh", response_model=TokenPair)
async def refresh_token(
        response: Response,
        user: models.UP = Depends(current_user)
):
    # Генерируем новую пару токенов
    access_token = await auth_backend.login(strategy=get_access_strategy(), user=user)
    refresh_token = await refresh_backend.login(strategy=get_refresh_strategy(), user=user)

    # Устанавливаем куки
    await auth_backend.transport.get_login_response(access_token, response)
    await refresh_backend.transport.get_login_response(refresh_token, response)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Tokens have been updated successfully!"},
    )


@auth_router.post("/access-token")
async def get_access_token(
        response: Response,
        user: models.UP = Depends(current_user)
):
    # Генерируем только access токен
    access_token = await auth_backend.login(strategy=get_access_strategy(), user=user)
    await auth_backend.transport.get_login_response(access_token, response)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Access token successfully updated!"},
    )


@auth_router.post("/logout")
async def logout(
        response: Response,
        user: models.UP = Depends(current_user),
):
    # Удаляем куки с токенами
    await auth_backend.transport.get_logout_response(response)
    await refresh_backend.transport.get_logout_response(response)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Successfully logged out"},
    )


app.include_router(auth_router)


router = APIRouter(
    tags=["Authorization"]
)


async def is_admin(user: User = Depends(current_user), session: AsyncSession = Depends(get_async_session)
                   ) -> bool:
    await session.refresh(user, ["role"])  # Явно обновляем связь
    return user.role.name == "admin"


@router.get("/protected-user", response_class=HTMLResponse)
async def protected_user_route(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse(
        "converter.html",
        {
            "request": request,
            "user": user
        }
    )


@router.get("/protected-admin", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def protected_admin_route(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse(
        "converter_for_admin.html",
        {
            "request": request,
            "user": user
        }
    )


@router.post("/convert-for-user", response_class=HTMLResponse)
async def protected_user_route(request: Request, user: User = Depends(current_user), from_: str = Form(...), to: str = Form(...), amount: str = Form(...)):
    """
    :param from_:
        This option is intended for the currency we are converting.

    :param to:
        This is the volute we are converting to.

    :param amount:
        Number of currencies convertible.

    :return:
        json response
    """
    try:
        url = f"https://api.apilayer.com/currency_data/convert?to={to}&from={from_}&amount={amount}"
        headers = {"apikey": settings.CURRENCY_API_KEY}
        response = requests.get(url, headers=headers)
        result = response.json()
        return templates.TemplateResponse("converter.html", {"request": request, "user": user, "result": result})
    except Exception as error:
        return templates.TemplateResponse("converter.html", {"request": request, "error": str(error)})



@router.post("/convert-for-admin", response_class=HTMLResponse, dependencies=[Depends(is_admin)])
async def protected_admin_route(request: Request, user: User = Depends(current_user), from_: str = Form(...), to: str = Form(...), amount: str = Form(...)):
    """
    :param from_:
        This option is intended for the currency we are converting.

    :param to:
        This is the volute we are converting to.

    :param amount:
        Number of currencies convertible.

    :return:
        json response
    """
    try:
        url = f"https://api.apilayer.com/currency_data/convert?to={to}&from={from_}&amount={amount}"
        headers = {"apikey": settings.CURRENCY_API_KEY}
        response = requests.get(url, headers=headers)
        result = response.json()
        return templates.TemplateResponse("converter_for_admin.html", {"request": request, "user": user, "result": result})
    except Exception as error:
        return templates.TemplateResponse("converter_for_admin.html", {"request": request, "error": str(error)})

"""
Если пользователь не аутентифицирован, current_user в is_admin() выбросит 401 Unauthorized;
Затем выполняется проверка user.role.name == "admin";
Если проверка не проходит, возвращается 403 Forbidden;

FastAPI автоматически возвращает 403 Forbidden, если зависимость в dependencies=[...] вернула False.
Это часть встроенной логики Depends() для удобства реализации RBAC (Role Based Access Control (рус. Управление доступом на основе ролей)).
"""

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
