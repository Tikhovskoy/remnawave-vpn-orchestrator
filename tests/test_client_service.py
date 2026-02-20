"""Unit-тесты бизнес-логики ClientService."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.client import Client, ClientStatus
from app.models.operation import ActionType, OperationResult
from app.services.client import ClientService
from app.services.remnawave import RemnawaveService, RemnawaveUserResult
from app.exceptions.handlers import (
    ClientAlreadyBlockedError,
    ClientAlreadyExistsError,
    ClientNotBlockedError,
    ClientNotFoundError,
)


# ── Фикстуры ────────────────────────────────────────────


def _make_client(
    status: ClientStatus = ClientStatus.ACTIVE,
    days_until_expire: int = 30,
) -> Client:
    """Вспомогательная функция — создать тестового клиента."""
    client = Client(
        id=uuid.uuid4(),
        username="test_user",
        remnawave_uuid="rw-uuid-123",
        short_uuid="short-abc",
        subscription_url="https://vpn.example.com/sub/test_user",
        status=status,
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=days_until_expire),
    )
    return client


def _make_rw_result() -> RemnawaveUserResult:
    """Вспомогательная функция — создать результат RemnaWave."""
    return RemnawaveUserResult(
        uuid="rw-uuid-123",
        username="test_user",
        short_uuid="short-abc",
        subscription_url="https://vpn.example.com/sub/test_user",
        status="active",
    )


def _make_service(
    client_repo_mock: MagicMock | None = None,
    operation_repo_mock: MagicMock | None = None,
    remnawave_mock: MagicMock | None = None,
) -> ClientService:
    """Создать ClientService с замоканными зависимостями."""
    session_mock = AsyncMock()
    remnawave = remnawave_mock or AsyncMock(spec=RemnawaveService)

    service = ClientService(session=session_mock, remnawave=remnawave)

    # Подменяем репозитории моками
    if client_repo_mock:
        service._client_repo = client_repo_mock
    else:
        service._client_repo = AsyncMock()

    if operation_repo_mock:
        service._operation_repo = operation_repo_mock
    else:
        service._operation_repo = AsyncMock()

    return service


# ── Тесты: продление подписки ────────────────────────────


@pytest.mark.asyncio
async def test_extend_subscription_adds_days_to_future_expiry() -> None:
    """Продление активной подписки: дни прибавляются к текущей дате истечения."""
    client = _make_client(days_until_expire=15)
    original_expires = client.expires_at

    remnawave_mock = AsyncMock(spec=RemnawaveService)
    remnawave_mock.update_expire_at = AsyncMock(return_value=_make_rw_result())

    service = _make_service(remnawave_mock=remnawave_mock)
    service._client_repo.get_by_id = AsyncMock(return_value=client)
    service._client_repo.update = AsyncMock(return_value=client)

    result = await service.extend_subscription(client_id=client.id, days=10)

    # Проверяем: новая дата = старая + 10 дней
    expected = original_expires + timedelta(days=10)
    assert abs((result.expires_at - expected).total_seconds()) < 5

    # Проверяем: аудит записан
    service._operation_repo.create.assert_called_once()
    call_kwargs = service._operation_repo.create.call_args.kwargs
    assert call_kwargs["action"] == ActionType.EXTEND
    assert call_kwargs["result"] == OperationResult.SUCCESS


@pytest.mark.asyncio
async def test_extend_subscription_starts_from_now_if_expired() -> None:
    """Продление просроченной подписки: отсчёт от текущего момента."""
    client = _make_client(days_until_expire=-5)  # Просрочено на 5 дней

    remnawave_mock = AsyncMock(spec=RemnawaveService)
    remnawave_mock.update_expire_at = AsyncMock(return_value=_make_rw_result())

    service = _make_service(remnawave_mock=remnawave_mock)
    service._client_repo.get_by_id = AsyncMock(return_value=client)
    service._client_repo.update = AsyncMock(return_value=client)

    now_before = datetime.now(tz=timezone.utc)
    result = await service.extend_subscription(client_id=client.id, days=30)
    now_after = datetime.now(tz=timezone.utc)

    # Новая дата должна быть ~now + 30 дней (не от старой даты)
    expected_min = now_before + timedelta(days=30)
    expected_max = now_after + timedelta(days=30)
    assert expected_min <= result.expires_at <= expected_max


# ── Тесты: блокировка ───────────────────────────────────


@pytest.mark.asyncio
async def test_block_already_blocked_raises_error() -> None:
    """Блокировка уже заблокированного клиента → ошибка 409."""
    client = _make_client(status=ClientStatus.BLOCKED)

    service = _make_service()
    service._client_repo.get_by_id = AsyncMock(return_value=client)

    with pytest.raises(ClientAlreadyBlockedError):
        await service.block_client(client_id=client.id)


@pytest.mark.asyncio
async def test_unblock_active_client_raises_error() -> None:
    """Разблокировка активного клиента → ошибка 409."""
    client = _make_client(status=ClientStatus.ACTIVE)

    service = _make_service()
    service._client_repo.get_by_id = AsyncMock(return_value=client)

    with pytest.raises(ClientNotBlockedError):
        await service.unblock_client(client_id=client.id)


# ── Тесты: создание ─────────────────────────────────────


@pytest.mark.asyncio
async def test_create_duplicate_username_raises_error() -> None:
    """Создание клиента с существующим username → ошибка 409."""
    existing_client = _make_client()

    service = _make_service()
    service._client_repo.get_by_username = AsyncMock(return_value=existing_client)

    with pytest.raises(ClientAlreadyExistsError):
        await service.create_client(username="test_user", days=30)


@pytest.mark.asyncio
async def test_get_nonexistent_client_raises_error() -> None:
    """Получение несуществующего клиента → ошибка 404."""
    service = _make_service()
    service._client_repo.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(ClientNotFoundError):
        await service.get_client(client_id=uuid.uuid4())
