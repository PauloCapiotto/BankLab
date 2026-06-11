from pydantic import BaseModel

from app import models


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    message: str
    read_at: str | None
    created_at: str


def to_notification_out(notif: models.Notification) -> NotificationOut:
    return NotificationOut(
        id=str(notif.id),
        type=notif.type,
        title=notif.title,
        message=notif.message,
        read_at=notif.read_at.isoformat() if notif.read_at else None,
        created_at=notif.created_at.isoformat(),
    )
