# RemnaWave VPN Orchestrator

Бизнес-оркестратор для управления VPN-клиентами через [RemnaWave](https://github.com/remnawave/backend).

## Стек

- **Python 3.12** + **FastAPI** + **uvicorn**
- **SQLAlchemy** (async) + **asyncpg** + **PostgreSQL**
- **Alembic** — миграции БД
- **RemnaWave Python SDK** — интеграция с панелью
- **Docker Compose** — инфраструктура
- **Caddy** — reverse proxy для RemnaWave
- **uv** — менеджер зависимостей

## Архитектура

```
Роутеры (API) → Сервисы (бизнес-логика) → Репозитории (БД)
                       ↓
              RemnaWave SDK (адаптер)
```

Слоистая архитектура (Controllers → Services → Repositories) с Dependency Injection через FastAPI.

## Быстрый старт

### 1. Клонировать проект

```bash
git clone <repo-url>
cd remnawave-orchestrator
```

### 2. Подготовить конфигурацию

```bash
cp .env.example .env
```

### 3. Запустить все сервисы

```bash
docker compose up -d --build
```

Запустятся:
- **Оркестратор** — `localhost:8000` (API, Swagger: `localhost:8000/docs`)
- **Caddy** — reverse proxy (`localhost:3000`), проксирует запросы к RemnaWave
- **RemnaWave** — панель управления (доступна через Caddy на `localhost:3000`)
- **PostgreSQL RemnaWave** — `localhost:6767`
- **Redis (Valkey)** — внутренняя сеть
- **PostgreSQL оркестратора** — `localhost:5433`

Миграции БД применяются автоматически при старте контейнера оркестратора.

### 4. Настроить API-токен

1. Открыть панель RemnaWave: `http://localhost:3000`
2. Создать учётную запись администратора
3. Перейти в раздел **API Tokens** и выпустить новый токен
4. Вписать полученный токен в `.env` → `REMNAWAVE_API_TOKEN`
5. Перезапустить оркестратор:

```bash
docker compose up -d --force-recreate orchestrator
```

### Локальная разработка (без Docker для оркестратора)

```powershell
docker compose up -d orchestrator-db remnawave-db remnawave-redis remnawave caddy
uv venv
.\.venv\Scripts\activate
uv sync
alembic upgrade head
uvicorn app.main:app --reload --app-dir src
```

Сервис доступен: `http://localhost:8000`

## API

Все эндпоинты: `http://localhost:8000/docs` (Swagger UI)

### Клиенты

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/clients` | Создать клиента |
| `GET` | `/api/v1/clients` | Список (фильтры: `status`, `expired`) |
| `GET` | `/api/v1/clients/{id}` | Карточка клиента |
| `DELETE` | `/api/v1/clients/{id}` | Удалить клиента |

### Подписка

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/clients/{id}/extend` | Продлить на N дней |

### Доступ

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/v1/clients/{id}/block` | Заблокировать |
| `POST` | `/api/v1/clients/{id}/unblock` | Разблокировать |

### Конфигурация

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/v1/clients/{id}/config` | Получить конфиг (base64) |
| `POST` | `/api/v1/clients/{id}/config/rotate` | Перевыпустить конфиг/ключ |

### Аудит

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/v1/operations?client_id=...` | Журнал операций |

## Модель данных

### clients

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | PK |
| `username` | VARCHAR(255) | Имя пользователя (уникальное) |
| `remnawave_uuid` | VARCHAR(255) | UUID в RemnaWave |
| `short_uuid` | VARCHAR(255) | Короткий UUID подписки |
| `subscription_url` | VARCHAR(1024) | URL подписки |
| `status` | ENUM(active, blocked) | Статус |
| `expires_at` | TIMESTAMPTZ | Дата истечения подписки |
| `created_at` | TIMESTAMPTZ | Дата создания |
| `updated_at` | TIMESTAMPTZ | Дата обновления |

### operations

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | PK |
| `client_id` | UUID → clients.id | FK |
| `action` | ENUM | Тип операции |
| `payload` | JSON | Данные операции |
| `result` | ENUM(success, fail) | Результат |
| `error` | TEXT | Текст ошибки |
| `created_at` | TIMESTAMPTZ | Время операции |

## Поведение DELETE

`DELETE /api/v1/clients/{id}` **полностью удаляет** клиента:
1. Удаляет пользователя из RemnaWave (отключает VPN-доступ)
2. Удаляет запись из локальной БД (каскадно удаляются операции)

Операция **необратима**.

## Формат конфигурации

`GET /api/v1/clients/{id}/config` возвращает:

```json
{
  "client_id": "uuid",
  "short_uuid": "abc123",
  "subscription_url": "https://vpn.example.com/sub/user",
  "config_data": "base64-encoded-subscription-config"
}
```

`config_data` — строка в формате base64, содержащая конфигурацию подписки RemnaWave.

## Ротация конфигурации

`POST /api/v1/clients/{id}/config/rotate` вызывает `revoke_subscription` в RemnaWave, что:
- Генерирует новый `short_uuid`
- Обновляет `subscription_url`
- **Старая конфигурация перестаёт работать**

## Дополнительные возможности

1. **Аудит** — все операции записываются в таблицу `operations`, доступны через `GET /api/v1/operations?client_id=...`
2. **Авто-деактивация** — метод `deactivate_expired()` в ClientService блокирует клиентов с `expires_at < now()`
3. **Защита от дублей** — проверка уникальности `username` перед созданием, идемпотентная проверка `status` при блокировке/разблокировке

## Тесты

```bash
pytest tests/ -v
```

## Структура проекта

```
src/app/
├── main.py               # Фабрика приложения
├── config.py             # Конфигурация (pydantic-settings)
├── database/
│   └── session.py        # Async SQLAlchemy
├── models/
│   ├── base.py           # DeclarativeBase
│   ├── client.py         # Модель Client
│   └── operation.py      # Модель Operation
├── repositories/
│   ├── client.py         # ClientRepository
│   └── operation.py      # OperationRepository
├── services/
│   ├── client.py         # ClientService (бизнес-логика)
│   └── remnawave.py      # RemnaWave SDK адаптер
├── api/
│   ├── dependencies.py   # DI-провайдеры
│   └── v1/
│       ├── router.py     # Агрегатный роутер
│       ├── clients.py    # /clients эндпоинты
│       └── operations.py # /operations эндпоинт
├── schemas/
│   ├── client.py         # DTO клиентов
│   └── operation.py      # DTO операций
└── exceptions/
    └── handlers.py       # HTTP-исключения

Caddyfile                 # Конфигурация reverse proxy
```
