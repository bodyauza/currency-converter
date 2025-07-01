from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, Request, Form, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from src.auth.manager import get_user_manager
from src.config import settings
from database import Base, engine
from src.auth.auth_config import fastapi_users, auth_backend, current_user, current_refresh_user, \
    refresh_backend, get_refresh_strategy, get_access_strategy
from src.auth.models import User
from src.auth.schemas import UserRead, UserCreate, TokenPair

from fastapi import Response, status
from fastapi.responses import JSONResponse
from fastapi_users import models


"""
1. Логин пользователя:
   - Пользователь отправляет email и пароль
   - Если данные верны, сервер генерирует:
     - access_token (короткоживущий, 5 минут) - в куках access_token
     - refresh_token (долгоживущий, 30 дней) - в куках refresh_token

2. Доступ к защищенным маршрутам:
   - Клиент отправляет access_token в заголовках
   - Если токен истек (401 ошибка), клиент запрашивает новый через /auth/access-token

3. Обновление access токена:
   - Клиент отправляет refresh_token на /auth/access-token
   - Сервер проверяет токен и возвращает новый access_token

4. Полное обновление токенов:
   - Когда refresh_token почти истек (осталось 1-5 дней), клиент отправляет его на /auth/refresh
   - Сервер возвращает новую пару токенов

5. Выход из системы:
   - При logout сервер очищает оба куки-файла
"""


templates = Jinja2Templates(directory="templates")

async def create_database():
    try:
        async with engine.begin() as conn:
            # Синхронно создает все таблицы из моделей, наследующих Base
            await conn.run_sync(Base.metadata.create_all)
        print("База данных успешно создана")
    except Exception as e:
        print(f"Ошибка при создании БД: {e}")


# Инициализация FastAPI с lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_database()
    yield

app = FastAPI(
    title='Currency Conversion',
    lifespan=lifespan
)


app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["Auth"],
)


app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Auth"],
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

router = APIRouter(
    tags=["Currency Conversion"]
)

@router.post("/", response_class=HTMLResponse)
async def currency_conversion(request: Request, from_: str = Form(...), to: str = Form(...), amount: str = Form(...)):
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
        return templates.TemplateResponse("index.html", {"request": request, "result": result})
    except Exception as error:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(error)})


def is_admin(user: User = Depends(current_user)) -> bool:
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


app.include_router(router)


# # Добавляем новые маршруты для работы с токенами
# auth_router = APIRouter(prefix="/auth", tags=["Auth"])
#
#
# @auth_router.post("/refresh", response_model=TokenPair)
# async def refresh_token(
#         response: Response,
#         user: models.UP = Depends(current_refresh_user)
# ):
#     # Генерируем новую пару токенов
#     access_token = await auth_backend.login(strategy=get_access_strategy(), user=user)
#     refresh_token = await refresh_backend.login(strategy=get_refresh_strategy(), user=user)
#
#     # Устанавливаем куки
#     await auth_backend.transport.set_login_response(access_token, response)
#     await refresh_backend.transport.set_login_response(refresh_token, response)
#
#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content={"message": "Tokens have been updated successfully!"},
#     )
#
#
# @auth_router.post("/access-token")
# async def get_access_token(
#         response: Response,
#         user: models.UP = Depends(current_refresh_user)
# ):
#     # Генерируем только access токен
#     access_token = await auth_backend.login(strategy=get_access_strategy(), user=user)
#     await auth_backend.transport.set_login_response(access_token, response)
#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content={"message": "Access token successfully updated!"},
#     )
#
#
# @auth_router.post("/logout")
# async def logout(
#         response: Response,
#         user: models.UP = Depends(current_user),
# ):
#     # Удаляем куки с токенами
#     await auth_backend.transport.set_logout_response(response)
#     await refresh_backend.transport.set_logout_response(response)
#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content={"message": "Successfully logged out"},
#     )
#
#
# app.include_router(auth_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
