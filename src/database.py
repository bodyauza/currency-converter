from typing import AsyncGenerator
from sqlalchemy import MetaData, NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.config import settings


metadata = MetaData()

class Base(DeclarativeBase):
    metadata = metadata  # Явная привязка


# Создаем асинхронный движок для подключения к базе данных с использованием NullPool (без пула соединений)
engine = create_async_engine(settings.ASYNC_DATABASE_URL, poolclass=NullPool, echo=True)

# Создаем фабрику асинхронных сессий с использованием ранее созданного движка
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Асинхронная функция для получения сессии базы данных
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
