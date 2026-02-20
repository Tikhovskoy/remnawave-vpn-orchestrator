"""Конфигурация приложения — загрузка из переменных окружения."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Центральная конфигурация сервиса-оркестратора.

    Все значения читаются из переменных окружения или файла `.env`.
    Валидация выполняется автоматически через pydantic-settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Приложение ───────────────────────────────────────
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False

    # ── База данных (наш PostgreSQL оркестратора) ────────
    database_url: str

    # ── Интеграция с RemnaWave ───────────────────────────
    remnawave_base_url: str
    remnawave_api_token: str


def get_settings() -> Settings:
    """Создать и вернуть экземпляр настроек."""
    return Settings()  # type: ignore[call-arg]
