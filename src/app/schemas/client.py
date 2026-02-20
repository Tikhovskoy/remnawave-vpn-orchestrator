"""Pydantic-схемы запросов и ответов для клиентов (DTO)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.client import ClientStatus


# ── Запросы ──────────────────────────────────────────────


class ClientCreateRequest(BaseModel):
    """Тело запроса на создание клиента."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Уникальное имя пользователя",
        examples=["ivan_petrov"],
    )
    days: int = Field(
        default=30,
        ge=1,
        le=3650,
        description="Срок подписки в днях",
        examples=[30],
    )


class ClientExtendRequest(BaseModel):
    """Тело запроса на продление подписки."""

    days: int = Field(
        ...,
        ge=1,
        le=3650,
        description="Количество дней для продления",
        examples=[30],
    )


# ── Ответы ───────────────────────────────────────────────


class ClientResponse(BaseModel):
    """Ответ с данными клиента."""

    id: uuid.UUID
    username: str
    remnawave_uuid: str | None
    short_uuid: str | None
    subscription_url: str | None
    status: ClientStatus
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientCreateResponse(BaseModel):
    """Ответ при создании клиента — возвращаем только id."""

    id: uuid.UUID


class ClientListResponse(BaseModel):
    """Список клиентов с мета-информацией."""

    items: list[ClientResponse]
    total: int


class ConfigResponse(BaseModel):
    """Ответ с конфигурацией подключения клиента."""

    client_id: uuid.UUID
    short_uuid: str
    subscription_url: str
    config_data: str = Field(description="Конфигурация подписки (base64)")


class MessageResponse(BaseModel):
    """Общий ответ с сообщением."""

    message: str
