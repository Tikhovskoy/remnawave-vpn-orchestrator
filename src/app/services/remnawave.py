"""Сервис-адаптер для взаимодействия с RemnaWave через Python SDK.

Оборачивает вызовы SDK в единый интерфейс с обработкой ошибок.
Используется бизнес-логикой (ClientService) через Dependency Injection.
"""

from dataclasses import dataclass
from datetime import datetime

from remnawave import RemnawaveSDK
from remnawave.models import (
    CreateUserRequestDto,
    RevokeUserRequestDto,
    UpdateUserRequestDto,
)

from app.config import Settings


@dataclass
class RemnawaveUserResult:
    """Результат операции с пользователем RemnaWave."""

    uuid: str
    username: str
    short_uuid: str
    subscription_url: str
    status: str


class RemnawaveService:
    """Адаптер для работы с RemnaWave API через Python SDK.

    Инкапсулирует все вызовы к панели RemnaWave.
    Предоставляет типизированный интерфейс для бизнес-логики.

    Attributes:
        _sdk: Экземпляр RemnaWave SDK.
    """

    def __init__(self, settings: Settings) -> None:
        """Инициализация SDK-клиента.

        Args:
            settings: Конфигурация приложения с URL и токеном RemnaWave.
        """
        self._sdk = RemnawaveSDK(
            base_url=settings.remnawave_base_url,
            token=settings.remnawave_api_token,
        )

    async def create_user(
        self,
        username: str,
        expire_at: datetime,
    ) -> RemnawaveUserResult:
        """Создать пользователя в RemnaWave.

        Args:
            username: Уникальное имя пользователя.
            expire_at: Дата истечения подписки (UTC).

        Returns:
            Данные созданного пользователя.
        """
        user = await self._sdk.users.create_user(
            CreateUserRequestDto(
                username=username,
                status="ACTIVE",
                expire_at=expire_at,
            )
        )
        return RemnawaveUserResult(
            uuid=str(user.uuid),
            username=user.username,
            short_uuid=user.short_uuid,
            subscription_url=user.subscription_url,
            status=user.status,
        )

    async def get_user(self, remnawave_uuid: str) -> RemnawaveUserResult:
        """Получить пользователя по UUID из RemnaWave.

        Args:
            remnawave_uuid: UUID пользователя в RemnaWave.

        Returns:
            Данные пользователя.
        """
        user = await self._sdk.users.get_user_by_uuid(uuid=remnawave_uuid)
        return RemnawaveUserResult(
            uuid=str(user.uuid),
            username=user.username,
            short_uuid=user.short_uuid,
            subscription_url=user.subscription_url,
            status=user.status,
        )

    async def disable_user(self, remnawave_uuid: str) -> RemnawaveUserResult:
        """Заблокировать пользователя в RemnaWave (отключить доступ).

        Args:
            remnawave_uuid: UUID пользователя в RemnaWave.

        Returns:
            Обновлённые данные пользователя.
        """
        user = await self._sdk.users.disable_user(uuid=remnawave_uuid)
        return RemnawaveUserResult(
            uuid=str(user.uuid),
            username=user.username,
            short_uuid=user.short_uuid,
            subscription_url=user.subscription_url,
            status=user.status,
        )

    async def enable_user(self, remnawave_uuid: str) -> RemnawaveUserResult:
        """Разблокировать пользователя в RemnaWave (включить доступ).

        Args:
            remnawave_uuid: UUID пользователя в RemnaWave.

        Returns:
            Обновлённые данные пользователя.
        """
        user = await self._sdk.users.enable_user(uuid=remnawave_uuid)
        return RemnawaveUserResult(
            uuid=str(user.uuid),
            username=user.username,
            short_uuid=user.short_uuid,
            subscription_url=user.subscription_url,
            status=user.status,
        )

    async def delete_user(self, remnawave_uuid: str) -> None:
        """Удалить пользователя из RemnaWave.

        Args:
            remnawave_uuid: UUID пользователя в RemnaWave.
        """
        await self._sdk.users.delete_user(uuid=remnawave_uuid)

    async def update_expire_at(
        self,
        remnawave_uuid: str,
        expire_at: datetime,
    ) -> RemnawaveUserResult:
        """Обновить дату истечения подписки в RemnaWave.

        Args:
            remnawave_uuid: UUID пользователя в RemnaWave.
            expire_at: Новая дата истечения (UTC).

        Returns:
            Обновлённые данные пользователя.
        """
        user = await self._sdk.users.update_user(
            UpdateUserRequestDto(
                uuid=remnawave_uuid,
                expire_at=expire_at,
            )
        )
        return RemnawaveUserResult(
            uuid=str(user.uuid),
            username=user.username,
            short_uuid=user.short_uuid,
            subscription_url=user.subscription_url,
            status=user.status,
        )

    async def get_subscription_config(self, short_uuid: str) -> str:
        """Получить конфигурацию подписки (base64).

        Args:
            short_uuid: Короткий UUID подписки.

        Returns:
            Строка конфигурации в формате base64.
        """
        config: str = await self._sdk.subscription.get_subscription(
            short_uuid=short_uuid,
        )
        return config

    async def revoke_subscription(
        self,
        remnawave_uuid: str,
    ) -> RemnawaveUserResult:
        """Перевыпустить подписку (ротация ключа/short_uuid).

        Генерирует новый short_uuid и subscription_url.
        Старая конфигурация перестаёт работать.

        Args:
            remnawave_uuid: UUID пользователя в RemnaWave.

        Returns:
            Обновлённые данные с новым short_uuid.
        """
        user = await self._sdk.users.revoke_user_subscription(
            uuid=remnawave_uuid,
            body=RevokeUserRequestDto(),
        )
        return RemnawaveUserResult(
            uuid=str(user.uuid),
            username=user.username,
            short_uuid=user.short_uuid,
            subscription_url=user.subscription_url,
            status=user.status,
        )
