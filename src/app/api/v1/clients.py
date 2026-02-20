"""Роутеры API v1 — эндпоинты управления клиентами VPN."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_client_service
from app.models.client import ClientStatus
from app.schemas.client import (
    ClientCreateRequest,
    ClientCreateResponse,
    ClientExtendRequest,
    ClientListResponse,
    ClientResponse,
    ConfigResponse,
    MessageResponse,
)
from app.services.client import ClientService

router = APIRouter(prefix="/clients", tags=["клиенты"])


# ── CRUD ─────────────────────────────────────────────────


@router.post(
    "",
    response_model=ClientCreateResponse,
    status_code=201,
    summary="Создать клиента",
)
async def create_client(
    body: ClientCreateRequest,
    service: ClientService = Depends(get_client_service),
) -> ClientCreateResponse:
    """Создать нового VPN-клиента.

    Создаёт пользователя в RemnaWave и сохраняет данные локально.
    """
    client = await service.create_client(
        username=body.username,
        days=body.days,
    )
    return ClientCreateResponse(id=client.id)


@router.get(
    "",
    response_model=ClientListResponse,
    summary="Список клиентов",
)
async def list_clients(
    status: ClientStatus | None = Query(
        default=None,
        description="Фильтр по статусу: active / blocked",
    ),
    expired: bool | None = Query(
        default=None,
        description="Фильтр по истечению подписки: true = просроченные",
    ),
    service: ClientService = Depends(get_client_service),
) -> ClientListResponse:
    """Получить список клиентов с фильтрацией."""
    clients, total = await service.get_clients(status=status, expired=expired)
    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in clients],
        total=total,
    )


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Карточка клиента",
)
async def get_client(
    client_id: uuid.UUID,
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    """Получить подробную информацию о клиенте."""
    client = await service.get_client(client_id)
    return ClientResponse.model_validate(client)


@router.delete(
    "/{client_id}",
    response_model=MessageResponse,
    summary="Удалить клиента",
)
async def delete_client(
    client_id: uuid.UUID,
    service: ClientService = Depends(get_client_service),
) -> MessageResponse:
    """Удалить клиента из системы и RemnaWave.

    Полностью удаляет запись клиента и его данные в RemnaWave.
    Операция необратима.
    """
    await service.delete_client(client_id)
    return MessageResponse(message="Клиент успешно удалён")


# ── Подписка ─────────────────────────────────────────────


@router.post(
    "/{client_id}/extend",
    response_model=ClientResponse,
    summary="Продлить подписку",
)
async def extend_subscription(
    client_id: uuid.UUID,
    body: ClientExtendRequest,
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    """Продлить подписку клиента на N дней.

    Если подписка истекла — отсчёт от текущего момента.
    Если ещё активна — дни прибавляются к текущей дате истечения.
    """
    client = await service.extend_subscription(
        client_id=client_id,
        days=body.days,
    )
    return ClientResponse.model_validate(client)


# ── Доступ ───────────────────────────────────────────────


@router.post(
    "/{client_id}/block",
    response_model=ClientResponse,
    summary="Заблокировать клиента",
)
async def block_client(
    client_id: uuid.UUID,
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    """Заблокировать клиента — отключить VPN-доступ в RemnaWave."""
    client = await service.block_client(client_id)
    return ClientResponse.model_validate(client)


@router.post(
    "/{client_id}/unblock",
    response_model=ClientResponse,
    summary="Разблокировать клиента",
)
async def unblock_client(
    client_id: uuid.UUID,
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    """Разблокировать клиента — включить VPN-доступ в RemnaWave."""
    client = await service.unblock_client(client_id)
    return ClientResponse.model_validate(client)


# ── Конфигурация ─────────────────────────────────────────


@router.get(
    "/{client_id}/config",
    response_model=ConfigResponse,
    summary="Получить конфигурацию",
)
async def get_config(
    client_id: uuid.UUID,
    service: ClientService = Depends(get_client_service),
) -> ConfigResponse:
    """Получить данные подключения / конфигурацию клиента.

    Формат: base64-строка конфигурации подписки из RemnaWave.
    """
    data = await service.get_config(client_id)
    return ConfigResponse(**data)


@router.post(
    "/{client_id}/config/rotate",
    response_model=ClientResponse,
    summary="Перевыпустить конфигурацию",
)
async def rotate_config(
    client_id: uuid.UUID,
    service: ClientService = Depends(get_client_service),
) -> ClientResponse:
    """Перевыпустить конфигурацию / ключ подписки.

    Генерирует новый short_uuid в RemnaWave.
    Старая конфигурация перестаёт работать.
    """
    client = await service.rotate_config(client_id)
    return ClientResponse.model_validate(client)
