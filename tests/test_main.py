import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock
from src.auth.models import User, Role
from src.auth.schemas import UserCreate
from src.database import get_async_session
from src.main import app, lifespan, create_clients_db


@pytest.fixture
def client():
    with TestClient(app) as client:  # TestClient создает HTTP-клиент,
        # который имитирует реальные запросы к FastAPI-приложению без запуска сервера
        yield client


@pytest.fixture
async def async_session():
    session = await get_async_session()
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
async def test_user(async_session: AsyncSession):
    role = Role(name="user", permissions={})
    async_session.add(role)
    await async_session.commit()

    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashedpassword",
        role_id=role.id,
        is_active=True
    )
    async_session.add(user)
    await async_session.commit()
    return user


@pytest.fixture
async def test_admin(async_session: AsyncSession):
    role = Role(name="admin", permissions={})
    async_session.add(role)
    await async_session.commit()

    user = User(
        email="admin@example.com",
        username="admin",
        hashed_password="hashedpassword",
        role_id=role.id,
        is_active=True,
        is_superuser=True
    )
    async_session.add(user)
    await async_session.commit()
    return user


@pytest.fixture
def mock_currency_api():
    with patch('main.requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def mock_user_manager():
    with patch('src.auth.manager.UserManager') as mock:
        yield mock


@pytest.fixture
def mock_auth_backend():
    with patch('main.auth_backend') as mock:
        yield mock


@pytest.fixture
def mock_refresh_backend():
    with patch('main.refresh_backend') as mock:
        yield mock


# Тесты для основных функций


@pytest.mark.asyncio
async def test_create_clients_db():
    # Мокируем все внешние зависимости
    with patch('main.database_exists', return_value=False) as mock_db_exists, \
            patch('main.create_database') as mock_create_db, \
            patch('main.Base.metadata.create_all') as mock_create_all:
        await create_clients_db()  # Вызываем тестируемую функцию
        # Проверяем, что все моки были вызваны
        mock_db_exists.assert_called_once()
        mock_create_db.assert_called_once()
        mock_create_all.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan():
    mock_app = MagicMock(spec=FastAPI)
    async with lifespan(mock_app) as _:
        pass


# Тесты для маршрутов


def test_protected_user_route(client, test_user):
    with patch('main.current_user', return_value=test_user):
        response = client.get("/protected-user")
        assert response.status_code == 200


def test_protected_admin_route(client, test_admin):
    with patch('main.current_user', return_value=test_admin), \
            patch('main.is_admin', return_value=True):
        response = client.get("/protected-admin")
        assert response.status_code == 200


"""

url = f"https://api.apilayer.com/currency_data/convert?to={to}&from={from_}&amount={amount}"
headers = {"apikey": settings.CURRENCY_API_KEY}
response = requests.get(url, headers=headers)
result = response.json()

"""

def test_convert_for_user(client, test_user, mock_currency_api):

    mock_response = MagicMock()
    mock_response.json.return_value = {"result": 100}
    mock_currency_api.return_value = mock_response  # Когда тестируемый код вызовет requests.get() - получит mock_response

    with patch('main.current_user', return_value=test_user):
        response = client.post("/convert-for-user", data={"from_": "USD", "to": "EUR", "amount": "100"})
        assert response.status_code == 200
        assert "result" in response.text


def test_convert_for_admin(client, test_admin, mock_currency_api):
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": 100}
    mock_currency_api.return_value = mock_response

    with patch('main.current_user', return_value=test_admin), \
            patch('main.is_admin', return_value=True):
        response = client.post("/convert-for-admin", data={"from_": "USD", "to": "EUR", "amount": "100"})
        assert response.status_code == 200
        assert "result" in response.text


# Тесты для аутентификации


def test_refresh_token(client, test_user, mock_auth_backend, mock_refresh_backend):

    mock_auth_backend.login.return_value = "new_access_token"
    mock_refresh_backend.login.return_value = "new_refresh_token"

    with patch('main.current_user', return_value=test_user):
        response = client.post("/auth/refresh")
        assert response.status_code == 200
        assert "Tokens have been updated successfully" in response.text


def test_get_access_token(client, test_user, mock_auth_backend):
    mock_auth_backend.login.return_value = "new_access_token"

    with patch('main.current_user', return_value=test_user):
        response = client.post("/auth/access-token")
        assert response.status_code == 200
        assert "Access token successfully updated" in response.text


def test_logout(client, test_user, mock_auth_backend, mock_refresh_backend):
    with patch('main.current_user', return_value=test_user):
        response = client.post("/auth/logout")
        assert response.status_code == 200
        assert "Successfully logged out" in response.text


# Тесты для обработки ошибок


def test_convert_for_user_error(client, test_user, mock_currency_api):
    mock_currency_api.side_effect = Exception("API error")  # Мок вызовет исключение

    with patch('main.current_user', return_value=test_user):
        response = client.post("/convert-for-user", data={"from_": "USD", "to": "EUR", "amount": "100"})
        assert response.status_code == 200
        assert "error" in response.text


def test_protected_admin_unauthorized(client, test_user):
    with patch('main.current_user', return_value=test_user), \
            patch('main.is_admin', return_value=False):
        response = client.get("/protected-admin")
        assert response.status_code == 403


# Тесты для UserManager


@pytest.mark.asyncio
async def test_user_manager_create(mock_user_manager):
    user_create = UserCreate(
        email="test@example.com",
        username="testuser",
        password="password",
        role_id=1
    )

    mock_manager = mock_user_manager.return_value

    # `spec=User` делает mock "типизированным", проверяя наличие атрибутов модели User
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.hashed_password = "hashed"
    mock_user.is_active = True
    mock_user.is_superuser = False
    mock_user.is_verified = False

    mock_manager.create.return_value = mock_user

    result = await mock_manager.create(user_create)
    assert result.email == "test@example.com"
    mock_manager.create.assert_called_once_with(user_create, safe=False, request=None)


@pytest.mark.asyncio
async def test_user_manager_authenticate(mock_user_manager):
    credentials = {"email": "test@example.com", "password": "password"}

    mock_manager = mock_user_manager.return_value

    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.hashed_password = "hashed"
    mock_user.is_active = True
    mock_user.is_superuser = False
    mock_user.is_verified = False

    mock_manager.authenticate.return_value = mock_user

    result = await mock_manager.authenticate(credentials)
    assert result.email == "test@example.com"
    mock_manager.authenticate.assert_called_once_with(credentials)