"""ORM-модель журнала операций (аудит)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ActionType(str, enum.Enum):
    """Типы операций над клиентами."""

    CREATE = "create"
    DELETE = "delete"
    EXTEND = "extend"
    BLOCK = "block"
    UNBLOCK = "unblock"
    GET_CONFIG = "get_config"
    ROTATE_CONFIG = "rotate_config"
    AUTO_DEACTIVATE = "auto_deactivate"


class OperationResult(str, enum.Enum):
    """Результат операции."""

    SUCCESS = "success"
    FAIL = "fail"


class Operation(Base):
    """Запись аудит-лога о выполненной операции.

    Каждое действие с клиентом (создание, блокировка, продление и т.д.)
    фиксируется в этой таблице.

    Attributes:
        id: Уникальный идентификатор операции (UUID).
        client_id: Ссылка на клиента.
        action: Тип действия (create, block, extend и т.д.).
        payload: Входные данные операции в формате JSON.
        result: Результат операции (success / fail).
        error: Текст ошибки (если result = fail).
        created_at: Время выполнения операции.
    """

    __tablename__ = "operations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Ссылка на клиента",
    )
    action: Mapped[ActionType] = mapped_column(
        Enum(ActionType, name="action_type", create_constraint=True),
        nullable=False,
        comment="Тип операции",
    )
    payload: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Входные данные операции (JSON)",
    )
    result: Mapped[OperationResult] = mapped_column(
        Enum(OperationResult, name="operation_result", create_constraint=True),
        nullable=False,
        comment="Результат: success / fail",
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Текст ошибки (при fail)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Связь с клиентом ─────────────────────────────────
    client: Mapped["Client"] = relationship(
        back_populates="operations",
    )

    def __repr__(self) -> str:
        return f"<Operation {self.action.value} → {self.result.value}>"


# Импорт внизу для избежания циклических зависимостей
from app.models.client import Client  # noqa: E402
