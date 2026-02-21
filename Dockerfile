# ── Этап сборки ──────────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /build

# Сначала зависимости (кэширование слоёв Docker)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Копируем исходный код и Alembic
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# ── Этап запуска ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Копируем виртуальное окружение и код из сборщика
COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src /app/src
COPY --from=builder /build/alembic /app/alembic
COPY --from=builder /build/alembic.ini /app/alembic.ini

# Добавляем venv в PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
