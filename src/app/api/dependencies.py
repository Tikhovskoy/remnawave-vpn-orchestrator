"""Провайдеры зависимостей FastAPI (Dependency Injection).

Центральная точка конфигурации DI: все сервисы и зависимости
создаются и предоставляются через функции-провайдеры.
"""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.session import get_audit_session, get_session
from app.services.client import ClientService
from app.services.remnawave import RemnawaveService


@lru_cache(maxsize=1)
def _create_remnawave_service() -> RemnawaveService:
    """Внутренний фабричный метод — синглтон RemnaWave-сервиса."""
    settings = get_settings()
    return RemnawaveService(settings)


def get_remnawave_service() -> RemnawaveService:
    """Провайдер сервиса RemnaWave.

    Переиспользует один экземпляр SDK-клиента
    на весь жизненный цикл приложения.
    """
    return _create_remnawave_service()


def get_client_service(
    session: AsyncSession = Depends(get_session),
    audit_session: AsyncSession = Depends(get_audit_session),
    remnawave: RemnawaveService = Depends(get_remnawave_service),
) -> ClientService:
    """Провайдер сервиса бизнес-логики клиентов.

    Создаётся на каждый запрос (т.к. привязан к сессии БД).

    Args:
        session: Асинхронная сессия SQLAlchemy.
        audit_session: Независимая сессия для аудит-логов ошибок.
        remnawave: Сервис RemnaWave.

    Returns:
        Экземпляр ClientService.
    """
    return ClientService(
        session=session,
        audit_session=audit_session,
        remnawave=remnawave,
    )
