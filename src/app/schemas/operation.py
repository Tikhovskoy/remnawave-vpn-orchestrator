"""Pydantic-схемы для журнала операций (DTO)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.operation import ActionType, OperationResult


class OperationResponse(BaseModel):
    """Ответ с данными операции из аудит-лога."""

    id: uuid.UUID
    client_id: uuid.UUID
    action: ActionType
    payload: dict[str, Any] | None
    result: OperationResult
    error: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OperationListResponse(BaseModel):
    """Список операций с мета-информацией."""

    items: list[OperationResponse]
    total: int
