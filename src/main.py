from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, Request, Form, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from src.config import settings
from database import Base, engine
from src.auth.auth_config import fastapi_users, auth_backend, current_user
from src.auth.models import User
from src.auth.schemas import UserRead, UserCreate


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

router = APIRouter(
    tags=['Currency Conversion']
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

app.include_router(router)

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

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
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

@app.get('/protected-user')
def protected_user(user: User = Depends(current_user)):
    return f"Hello {user.username} or email {user.email}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
