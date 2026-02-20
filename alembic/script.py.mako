"""Шаблон для автогенерации миграций Alembic.

Ревизия: ${up_revision}
Создана: ${create_date}
Сообщение: ${message}
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# Идентификаторы ревизии (используются Alembic)
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Применить миграцию (вперёд)."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Откатить миграцию (назад)."""
    ${downgrades if downgrades else "pass"}
