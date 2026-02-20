"""Репозиторий для работы с таблицей operations (аудит-лог)."""

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation import ActionType, Operation, OperationResult


class OperationRepository:
    """Объект доступа к данным журнала операций.

    Инкапсулирует все SQL-запросы к таблице `operations`.

    Attributes:
        _session: Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        client_id: uuid.UUID,
        action: ActionType,
        result: OperationResult,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> Operation:
        """Создать запись аудит-лога.

        Args:
            client_id: UUID клиента.
            action: Тип выполненной операции.
            result: Результат операции (success / fail).
            payload: Входные данные операции.
            error: Текст ошибки (если fail).

        Returns:
            Созданная запись операции.
        """
        operation = Operation(
            client_id=client_id,
            action=action,
            payload=payload,
            result=result,
            error=error,
        )
        self._session.add(operation)
        await self._session.flush()
        await self._session.refresh(operation)
        return operation

    async def get_by_client_id(
        self,
        client_id: uuid.UUID,
    ) -> tuple[list[Operation], int]:
        """Получить операции по UUID клиента.

        Args:
            client_id: UUID клиента.

        Returns:
            Кортеж (список операций, общее количество).
        """
        stmt = (
            select(Operation)
            .where(Operation.client_id == client_id)
            .order_by(Operation.created_at.desc())
        )
        count_stmt = select(func.count(Operation.id)).where(
            Operation.client_id == client_id
        )

        result = await self._session.execute(stmt)
        operations = list(result.scalars().all())

        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        return operations, total
