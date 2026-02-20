"""Сервис бизнес-логики управления клиентами VPN.

Оркестрирует работу между репозиторием (БД) и адаптером RemnaWave.
Все операции логируются в таблицу operations (аудит).
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.handlers import (
    ClientAlreadyBlockedError,
    ClientAlreadyExistsError,
    ClientConfigUnavailableError,
    ClientNotBlockedError,
    ClientNotFoundError,
    RemnawaveIntegrationError,
)
from app.models.client import Client, ClientStatus
from app.models.operation import ActionType, OperationResult
from app.repositories.client import ClientRepository
from app.repositories.operation import OperationRepository
from app.services.remnawave import RemnawaveService


class ClientService:
    """Основной сервис управления жизненным циклом VPN-клиентов.

    Обеспечивает:
    - Создание / удаление клиентов (с синхронизацией в RemnaWave).
    - Продление подписки.
    - Блокировку / разблокировку (с отключением доступа в RemnaWave).
    - Получение и ротацию конфигурации.
    - Запись всех операций в аудит-лог.

    Attributes:
        _client_repo: Репозиторий клиентов.
        _operation_repo: Репозиторий операций (аудит).
        _remnawave: Адаптер RemnaWave SDK.
    """

    def __init__(
        self,
        session: AsyncSession,
        remnawave: RemnawaveService,
    ) -> None:
        self._client_repo = ClientRepository(session)
        self._operation_repo = OperationRepository(session)
        self._remnawave = remnawave

    # ── Создание клиента ─────────────────────────────────

    async def create_client(self, username: str, days: int = 30) -> Client:
        """Создать нового VPN-клиента.

        1. Проверяет уникальность username в нашей БД.
        2. Создаёт пользователя в RemnaWave.
        3. Сохраняет клиента в локальную БД.
        4. Пишет аудит-лог.

        Args:
            username: Уникальное имя пользователя.
            days: Срок подписки в днях (по умолчанию 30).

        Returns:
            Созданный клиент.

        Raises:
            ClientAlreadyExistsError: Клиент с таким username уже есть.
            RemnawaveIntegrationError: Ошибка создания в RemnaWave.
        """
        # Проверка на дубли
        existing = await self._client_repo.get_by_username(username)
        if existing is not None:
            raise ClientAlreadyExistsError(username)

        expire_at = datetime.now(tz=timezone.utc) + timedelta(days=days)

        # Создаём в RemnaWave
        try:
            rw_user = await self._remnawave.create_user(
                username=username,
                expire_at=expire_at,
            )
        except Exception as exc:
            raise RemnawaveIntegrationError(str(exc)) from exc

        # Сохраняем локально
        client = Client(
            username=username,
            remnawave_uuid=rw_user.uuid,
            short_uuid=rw_user.short_uuid,
            subscription_url=rw_user.subscription_url,
            status=ClientStatus.ACTIVE,
            expires_at=expire_at,
        )
        client = await self._client_repo.create(client)

        # Аудит
        await self._operation_repo.create(
            client_id=client.id,
            action=ActionType.CREATE,
            payload={"username": username, "days": days},
            result=OperationResult.SUCCESS,
        )

        return client

    # ── Получение клиентов ───────────────────────────────

    async def get_client(self, client_id: uuid.UUID) -> Client:
        """Получить клиента по UUID.

        Args:
            client_id: UUID клиента.

        Returns:
            Клиент.

        Raises:
            ClientNotFoundError: Клиент не найден.
        """
        client = await self._client_repo.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundError(str(client_id))
        return client

    async def get_clients(
        self,
        status: ClientStatus | None = None,
        expired: bool | None = None,
    ) -> tuple[list[Client], int]:
        """Получить список клиентов с фильтрами.

        Args:
            status: Фильтр по статусу.
            expired: Фильтр по истечению подписки.

        Returns:
            Кортеж (список клиентов, общее количество).
        """
        return await self._client_repo.get_list(status=status, expired=expired)

    # ── Удаление клиента ─────────────────────────────────

    async def delete_client(self, client_id: uuid.UUID) -> None:
        """Удалить клиента.

        1. Удаляет пользователя в RemnaWave.
        2. Удаляет запись из локальной БД.
        3. Пишет аудит-лог.

        Args:
            client_id: UUID клиента.

        Raises:
            ClientNotFoundError: Клиент не найден.
        """
        client = await self.get_client(client_id)

        # Аудит пишем ДО удаления (иначе FK сломается)
        try:
            if client.remnawave_uuid:
                await self._remnawave.delete_user(client.remnawave_uuid)
            await self._operation_repo.create(
                client_id=client.id,
                action=ActionType.DELETE,
                payload=None,
                result=OperationResult.SUCCESS,
            )
        except Exception as exc:
            await self._operation_repo.create(
                client_id=client.id,
                action=ActionType.DELETE,
                payload=None,
                result=OperationResult.FAIL,
                error=str(exc),
            )
            raise RemnawaveIntegrationError(str(exc)) from exc

        await self._client_repo.delete(client)

    # ── Продление подписки ───────────────────────────────

    async def extend_subscription(
        self,
        client_id: uuid.UUID,
        days: int,
    ) -> Client:
        """Продлить подписку клиента на N дней.

        Если текущая дата истечения в прошлом — отсчёт от текущего момента.
        Если в будущем — прибавляет дни к существующей дате.

        Args:
            client_id: UUID клиента.
            days: Количество дней для продления.

        Returns:
            Обновлённый клиент.
        """
        client = await self.get_client(client_id)

        now = datetime.now(tz=timezone.utc)
        base_date = max(client.expires_at, now)
        new_expires_at = base_date + timedelta(days=days)

        try:
            if client.remnawave_uuid:
                await self._remnawave.update_expire_at(
                    remnawave_uuid=client.remnawave_uuid,
                    expire_at=new_expires_at,
                )
        except Exception as exc:
            await self._operation_repo.create(
                client_id=client.id,
                action=ActionType.EXTEND,
                payload={"days": days},
                result=OperationResult.FAIL,
                error=str(exc),
            )
            raise RemnawaveIntegrationError(str(exc)) from exc

        client.expires_at = new_expires_at
        client = await self._client_repo.update(client)

        await self._operation_repo.create(
            client_id=client.id,
            action=ActionType.EXTEND,
            payload={"days": days, "new_expires_at": new_expires_at.isoformat()},
            result=OperationResult.SUCCESS,
        )

        return client

    # ── Блокировка / Разблокировка ───────────────────────

    async def block_client(self, client_id: uuid.UUID) -> Client:
        """Заблокировать клиента (отключить VPN-доступ).

        Args:
            client_id: UUID клиента.

        Returns:
            Обновлённый клиент.

        Raises:
            ClientAlreadyBlockedError: Клиент уже заблокирован.
        """
        client = await self.get_client(client_id)

        if client.status == ClientStatus.BLOCKED:
            raise ClientAlreadyBlockedError()

        try:
            if client.remnawave_uuid:
                await self._remnawave.disable_user(client.remnawave_uuid)
        except Exception as exc:
            await self._operation_repo.create(
                client_id=client.id,
                action=ActionType.BLOCK,
                payload=None,
                result=OperationResult.FAIL,
                error=str(exc),
            )
            raise RemnawaveIntegrationError(str(exc)) from exc

        client.status = ClientStatus.BLOCKED
        client = await self._client_repo.update(client)

        await self._operation_repo.create(
            client_id=client.id,
            action=ActionType.BLOCK,
            payload=None,
            result=OperationResult.SUCCESS,
        )

        return client

    async def unblock_client(self, client_id: uuid.UUID) -> Client:
        """Разблокировать клиента (включить VPN-доступ).

        Args:
            client_id: UUID клиента.

        Returns:
            Обновлённый клиент.

        Raises:
            ClientNotBlockedError: Клиент не заблокирован.
        """
        client = await self.get_client(client_id)

        if client.status != ClientStatus.BLOCKED:
            raise ClientNotBlockedError()

        try:
            if client.remnawave_uuid:
                await self._remnawave.enable_user(client.remnawave_uuid)
        except Exception as exc:
            await self._operation_repo.create(
                client_id=client.id,
                action=ActionType.UNBLOCK,
                payload=None,
                result=OperationResult.FAIL,
                error=str(exc),
            )
            raise RemnawaveIntegrationError(str(exc)) from exc

        client.status = ClientStatus.ACTIVE
        client = await self._client_repo.update(client)

        await self._operation_repo.create(
            client_id=client.id,
            action=ActionType.UNBLOCK,
            payload=None,
            result=OperationResult.SUCCESS,
        )

        return client

    # ── Конфигурация ─────────────────────────────────────

    async def get_config(
        self,
        client_id: uuid.UUID,
    ) -> dict[str, str]:
        """Получить конфигурацию подключения клиента.

        Args:
            client_id: UUID клиента.

        Returns:
            Словарь с данными конфигурации.

        Raises:
            ClientConfigUnavailableError: Нет привязки к RemnaWave.
        """
        client = await self.get_client(client_id)

        if not client.short_uuid:
            raise ClientConfigUnavailableError()

        try:
            config_data = await self._remnawave.get_subscription_config(
                short_uuid=client.short_uuid,
            )
        except Exception as exc:
            await self._operation_repo.create(
                client_id=client.id,
                action=ActionType.GET_CONFIG,
                payload=None,
                result=OperationResult.FAIL,
                error=str(exc),
            )
            raise RemnawaveIntegrationError(str(exc)) from exc

        await self._operation_repo.create(
            client_id=client.id,
            action=ActionType.GET_CONFIG,
            payload=None,
            result=OperationResult.SUCCESS,
        )

        return {
            "client_id": str(client.id),
            "short_uuid": client.short_uuid,
            "subscription_url": client.subscription_url or "",
            "config_data": config_data,
        }

    async def rotate_config(self, client_id: uuid.UUID) -> Client:
        """Перевыпустить конфигурацию (ротация ключа).

        Вызывает revoke_subscription в RemnaWave, что генерирует
        новый short_uuid. Старая конфигурация перестаёт работать.

        Args:
            client_id: UUID клиента.

        Returns:
            Обновлённый клиент с новым short_uuid.

        Raises:
            ClientConfigUnavailableError: Нет привязки к RemnaWave.
        """
        client = await self.get_client(client_id)

        if not client.remnawave_uuid:
            raise ClientConfigUnavailableError()

        try:
            rw_user = await self._remnawave.revoke_subscription(
                remnawave_uuid=client.remnawave_uuid,
            )
        except Exception as exc:
            await self._operation_repo.create(
                client_id=client.id,
                action=ActionType.ROTATE_CONFIG,
                payload=None,
                result=OperationResult.FAIL,
                error=str(exc),
            )
            raise RemnawaveIntegrationError(str(exc)) from exc

        client.short_uuid = rw_user.short_uuid
        client.subscription_url = rw_user.subscription_url
        client = await self._client_repo.update(client)

        await self._operation_repo.create(
            client_id=client.id,
            action=ActionType.ROTATE_CONFIG,
            payload={"new_short_uuid": rw_user.short_uuid},
            result=OperationResult.SUCCESS,
        )

        return client

    # ── Авто-деактивация ─────────────────────────────────

    async def deactivate_expired(self) -> int:
        """Заблокировать всех активных клиентов с истёкшей подпиской.

        Для каждого просроченного клиента:
        1. Отключает доступ в RemnaWave.
        2. Меняет статус на BLOCKED в локальной БД.
        3. Пишет аудит-лог.

        Returns:
            Количество деактивированных клиентов.
        """
        expired_clients = await self._client_repo.get_expired_active()
        count = 0

        for client in expired_clients:
            try:
                if client.remnawave_uuid:
                    await self._remnawave.disable_user(client.remnawave_uuid)

                client.status = ClientStatus.BLOCKED
                await self._client_repo.update(client)

                await self._operation_repo.create(
                    client_id=client.id,
                    action=ActionType.AUTO_DEACTIVATE,
                    payload={"expired_at": client.expires_at.isoformat()},
                    result=OperationResult.SUCCESS,
                )
                count += 1
            except Exception as exc:
                await self._operation_repo.create(
                    client_id=client.id,
                    action=ActionType.AUTO_DEACTIVATE,
                    payload={"expired_at": client.expires_at.isoformat()},
                    result=OperationResult.FAIL,
                    error=str(exc),
                )

        return count
