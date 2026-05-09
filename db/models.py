from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class User:
    id: int | None
    telegram_id: int
    username: str | None
    is_active: bool
    notify_time: str
    created_at: datetime
    updated_at: datetime


@dataclass
class Subscription:
    id: int | None
    user_id: int
    category: str


@dataclass
class Holiday:
    id: int | None
    date: date
    name: str
    category: str
    description: str | None
    external_id: str | None


@dataclass
class NotificationLog:
    id: int | None
    user_id: int
    holiday_id: int
    sent_at: datetime
