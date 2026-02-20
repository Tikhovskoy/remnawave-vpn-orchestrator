"""Фабрика FastAPI-приложения и управление жизненным циклом."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Управление запуском и остановкой приложения.

    Заглушка для инициализации пула подключений к БД
    и SDK RemnaWave (будет реализовано на следующих шагах).
    """
    # ── Запуск ───────────────────────────────────────────
    settings = get_settings()
    app.state.settings = settings
    yield
    # ── Остановка ────────────────────────────────────────


def create_app() -> FastAPI:
    """Собрать и сконфигурировать экземпляр FastAPI-приложения."""
    settings = get_settings()

    app = FastAPI(
        title="RemnaWave VPN Orchestrator",
        description="Бизнес-оркестратор для управления VPN-клиентами через RemnaWave",
        version="0.1.0",
        debug=settings.app_debug,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── Проверка здоровья сервиса ────────────────────────
    @app.get("/health", tags=["система"])
    async def health_check() -> dict[str, str]:
        """Вернуть статус работоспособности сервиса."""
        return {"status": "ok"}

    return app


app = create_app()
