import datetime as dt
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.core.errors import APIError
from app.modules.auth.deps import get_current_user
from app.modules.notifications.schemas import NotificationOut, to_notification_out

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationOut]:
    result = await session.execute(
        select(models.Notification)
        .where(models.Notification.user_id == user.id)
        .order_by(models.Notification.created_at.desc())
    )
    return [to_notification_out(n) for n in result.scalars().all()]


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_as_read(
    notification_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationOut:
    result = await session.execute(
        select(models.Notification).where(
            models.Notification.id == notification_id,
            models.Notification.user_id == user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        raise APIError(404, "NOTIFICATION_NOT_FOUND", "Notificação não encontrada.")
    if notif.read_at is None:
        notif.read_at = dt.datetime.now(dt.timezone.utc)
        await session.commit()
        await session.refresh(notif)
    return to_notification_out(notif)
