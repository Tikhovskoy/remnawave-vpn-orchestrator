"""ORM-модель клиента VPN."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ClientStatus(str, enum.Enum):
    """Статусы клиента VPN."""

    ACTIVE = "active"
    BLOCKED = "blocked"


class Client(Base):
    """Модель клиента VPN-сервиса.

    Хранит локальные данные клиента, включая привязку
    к пользователю RemnaWave через remnawave_uuid.

    Attributes:
        id: Уникальный идентификатор клиента (UUID).
        username: Имя пользователя в RemnaWave.
        remnawave_uuid: UUID пользователя на стороне RemnaWave.
        short_uuid: Короткий UUID для подписки (из RemnaWave).
        subscription_url: URL подписки клиента.
        status: Текущий статус (active / blocked).
        expires_at: Дата истечения подписки.
        created_at: Дата создания записи.
        updated_at: Дата последнего обновления.
    """

    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="Имя пользователя в RemnaWave",
    )
    remnawave_uuid: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        comment="UUID пользователя на стороне RemnaWave",
    )
    short_uuid: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Короткий UUID подписки (из RemnaWave)",
    )
    subscription_url: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="URL подписки клиента",
    )
    status: Mapped[ClientStatus] = mapped_column(
        Enum(ClientStatus, name="client_status", create_constraint=True),
        default=ClientStatus.ACTIVE,
        nullable=False,
        comment="Статус клиента: active / blocked",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Дата истечения подписки",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Связь с аудит-логом ──────────────────────────────
    operations: Mapped[list["Operation"]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Client {self.username} [{self.status.value}]>"


# Импорт внизу для избежания циклических зависимостей
from app.models.operation import Operation  # noqa: E402
