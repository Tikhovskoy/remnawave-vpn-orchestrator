"""Роутеры API v1 — эндпоинты журнала операций (аудит)."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_client_service
from app.repositories.operation import OperationRepository
from app.database.session import get_session
from app.schemas.operation import OperationListResponse, OperationResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/operations", tags=["аудит"])


@router.get(
    "",
    response_model=OperationListResponse,
    summary="Журнал операций",
)
async def list_operations(
    client_id: uuid.UUID = Query(
        ...,
        description="UUID клиента для фильтрации операций",
    ),
    session: AsyncSession = Depends(get_session),
) -> OperationListResponse:
    """Получить журнал операций по клиенту.

    Возвращает все операции (аудит-лог) для указанного клиента,
    отсортированные по дате создания (новые — первыми).
    """
    repo = OperationRepository(session)
    operations, total = await repo.get_by_client_id(client_id)
    return OperationListResponse(
        items=[OperationResponse.model_validate(op) for op in operations],
        total=total,
    )
