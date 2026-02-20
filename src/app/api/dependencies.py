"""Провайдеры зависимостей FastAPI (Dependency Injection).

Центральная точка конфигурации DI: все сервисы и зависимости
создаются и предоставляются через функции-провайдеры.
"""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.session import get_session
from app.services.remnawave import RemnawaveService


@lru_cache(maxsize=1)
def get_remnawave_service(
    settings: Settings = Depends(get_settings),
) -> RemnawaveService:
    """Провайдер сервиса RemnaWave (синглтон через lru_cache).

    Создаёт один экземпляр RemnawaveService на весь жизненный цикл
    приложения, переиспользуя SDK-клиент.
    """
    return RemnawaveService(settings)
