"""Фабрика FastAPI-приложения и управление жизненным циклом."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import router as v1_router
from app.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Управление запуском и остановкой приложения."""
    # ── Запуск ───────────────────────────────────────────
    settings = get_settings()
    app.state.settings = settings
    logger.info("Оркестратор запущен на %s:%s", settings.app_host, settings.app_port)
    yield
    # ── Остановка ────────────────────────────────────────
    logger.info("Оркестратор остановлен")


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

    # ── Глобальная обработка ошибок ──────────────────────

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> ORJSONResponse:
        """Обработчик HTTP-исключений → единый JSON-формат."""
        return ORJSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> ORJSONResponse:
        """Обработчик ошибок валидации → понятный JSON."""
        return ORJSONResponse(
            status_code=422,
            content={
                "detail": "Ошибка валидации входных данных",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request,
        exc: Exception,
    ) -> ORJSONResponse:
        """Обработчик непредвиденных ошибок → 500 без утечки деталей."""
        logger.exception("Непредвиденная ошибка: %s", exc)
        return ORJSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера"},
        )

    # ── Роутеры ──────────────────────────────────────────
    app.include_router(v1_router)

    # ── Проверка здоровья сервиса ────────────────────────
    @app.get("/health", tags=["система"])
    async def health_check() -> dict[str, str]:
        """Вернуть статус работоспособности сервиса."""
        return {"status": "ok"}

    return app


app = create_app()
