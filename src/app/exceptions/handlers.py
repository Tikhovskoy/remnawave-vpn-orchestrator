"""Пользовательские исключения и глобальные обработчики ошибок."""

from fastapi import HTTPException, status


class ClientNotFoundError(HTTPException):
    """Клиент не найден."""

    def __init__(self, client_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Клиент с id={client_id} не найден",
        )


class ClientAlreadyExistsError(HTTPException):
    """Клиент с таким username уже существует."""

    def __init__(self, username: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Клиент с username='{username}' уже существует",
        )


class ClientAlreadyBlockedError(HTTPException):
    """Попытка заблокировать уже заблокированного клиента."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Клиент уже заблокирован",
        )


class ClientNotBlockedError(HTTPException):
    """Попытка разблокировать незаблокированного клиента."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Клиент не заблокирован",
        )


class ClientConfigUnavailableError(HTTPException):
    """Конфигурация недоступна (нет short_uuid)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Конфигурация клиента недоступна — отсутствует привязка к RemnaWave",
        )


class RemnawaveIntegrationError(HTTPException):
    """Ошибка взаимодействия с RemnaWave API."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка RemnaWave: {detail}",
        )
