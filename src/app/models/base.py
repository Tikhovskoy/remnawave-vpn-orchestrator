"""Декларативная база для всех ORM-моделей."""

from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy.

    Все ORM-модели должны наследоваться от этого класса,
    чтобы Alembic мог автоматически обнаруживать таблицы.
    """

    pass
