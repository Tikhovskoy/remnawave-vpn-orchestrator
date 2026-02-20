"""Асинхронный движок SQLAlchemy и фабрика сессий."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:  # type: ignore[misc]
    """Провайдер асинхронной сессии для Dependency Injection.

    Используется как зависимость FastAPI:
        session: AsyncSession = Depends(get_session)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_audit_session() -> AsyncSession:  # type: ignore[misc]
    """Независимая сессия для записи аудит-логов ошибок.

    Коммитится отдельно от основной транзакции, поэтому
    FAIL-записи сохраняются даже при rollback основной сессии.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
