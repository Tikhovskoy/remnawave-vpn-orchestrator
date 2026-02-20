"""Репозиторий для работы с таблицей clients."""

import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client, ClientStatus


class ClientRepository:
    """Объект доступа к данным клиентов.

    Инкапсулирует все SQL-запросы к таблице `clients`.
    Не содержит бизнес-логики — только чтение/запись в БД.

    Attributes:
        _session: Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, client: Client) -> Client:
        """Добавить нового клиента в БД.

        Args:
            client: Экземпляр модели Client для сохранения.

        Returns:
            Сохранённый клиент с заполненными серверными полями.
        """
        self._session.add(client)
        await self._session.flush()
        await self._session.refresh(client)
        return client

    async def get_by_id(self, client_id: uuid.UUID) -> Client | None:
        """Получить клиента по UUID.

        Args:
            client_id: UUID клиента.

        Returns:
            Клиент или None, если не найден.
        """
        return await self._session.get(Client, client_id)

    async def get_by_username(self, username: str) -> Client | None:
        """Получить клиента по имени пользователя.

        Args:
            username: Имя пользователя.

        Returns:
            Клиент или None, если не найден.
        """
        stmt = select(Client).where(Client.username == username)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        status: ClientStatus | None = None,
        expired: bool | None = None,
    ) -> tuple[list[Client], int]:
        """Получить список клиентов с фильтрацией.

        Args:
            status: Фильтр по статусу (active / blocked).
            expired: Фильтр по истечению подписки (True = просроченные).

        Returns:
            Кортеж (список клиентов, общее количество).
        """
        stmt = select(Client)
        count_stmt = select(func.count(Client.id))

        if status is not None:
            stmt = stmt.where(Client.status == status)
            count_stmt = count_stmt.where(Client.status == status)

        if expired is True:
            stmt = stmt.where(Client.expires_at < func.now())
            count_stmt = count_stmt.where(Client.expires_at < func.now())
        elif expired is False:
            stmt = stmt.where(Client.expires_at >= func.now())
            count_stmt = count_stmt.where(Client.expires_at >= func.now())

        stmt = stmt.order_by(Client.created_at.desc())

        result = await self._session.execute(stmt)
        clients = list(result.scalars().all())

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        return clients, total

    async def update(self, client: Client) -> Client:
        """Обновить данные клиента в БД.

        Args:
            client: Изменённый экземпляр клиента.

        Returns:
            Обновлённый клиент.
        """
        await self._session.flush()
        await self._session.refresh(client)
        return client

    async def delete(self, client: Client) -> None:
        """Удалить клиента из БД.

        Args:
            client: Клиент для удаления.
        """
        await self._session.delete(client)
        await self._session.flush()

    async def get_expired_active(self) -> list[Client]:
        """Получить активных клиентов с истёкшей подпиской.

        Используется для автоматической деактивации.

        Returns:
            Список активных клиентов, у которых expires_at < now().
        """
        stmt = select(Client).where(
            Client.status == ClientStatus.ACTIVE,
            Client.expires_at < func.now(),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
