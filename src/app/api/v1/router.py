"""Агрегатный роутер API версии 1.

Собирает все sub-роутеры в один роутер с общим префиксом /api/v1.
"""

from fastapi import APIRouter

from app.api.v1.clients import router as clients_router
from app.api.v1.operations import router as operations_router

router = APIRouter(prefix="/api/v1")

router.include_router(clients_router)
router.include_router(operations_router)
