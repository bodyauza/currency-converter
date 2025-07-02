from typing import AsyncGenerator
from sqlalchemy import MetaData, NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "postgresql+asyncpg://root:123@localhost:5432/clients"

class Base(DeclarativeBase): pass

metadata = MetaData()

# Создаем асинхронный движок для подключения к базе данных с использованием NullPool (без пула соединений)
engine = create_async_engine(DATABASE_URL, poolclass=NullPool)

# Создаем фабрику асинхронных сессий с использованием ранее созданного движка
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Асинхронная функция для получения сессии базы данных
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
