from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

import aiosqlite

from db.models import Holiday, NotificationLog, Subscription, User

DB_PATH = Path("celebrate_bot.db")

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    notify_time TEXT NOT NULL DEFAULT '07:00',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    category TEXT NOT NULL,
    UNIQUE(user_id, category)
);

CREATE TABLE IF NOT EXISTS holidays_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    external_id TEXT,
    UNIQUE(date, name, category)
);

CREATE TABLE IF NOT EXISTS notifications_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    holiday_id INTEGER NOT NULL REFERENCES holidays_cache(id),
    sent_at TEXT NOT NULL,
    UNIQUE(user_id, holiday_id)
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


class UserRepository:
    @staticmethod
    async def create(telegram_id: int, username: str | None) -> User:
        now = datetime.utcnow().isoformat()
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT INTO users (telegram_id, username, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (telegram_id, username, now, now),
            )
            await db.commit()
            return User(
                id=cursor.lastrowid,
                telegram_id=telegram_id,
                username=username,
                is_active=True,
                notify_time="07:00",
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )

    @staticmethod
    async def get_by_telegram_id(telegram_id: int) -> User | None:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            return User(
                id=row["id"],
                telegram_id=row["telegram_id"],
                username=row["username"],
                is_active=bool(row["is_active"]),
                notify_time=row["notify_time"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    @staticmethod
    async def get_active_subscribers() -> list[User]:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM users WHERE is_active = 1")
            rows = await cursor.fetchall()
            return [
                User(
                    id=row["id"],
                    telegram_id=row["telegram_id"],
                    username=row["username"],
                    is_active=bool(row["is_active"]),
                    notify_time=row["notify_time"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    @staticmethod
    async def deactivate(telegram_id: int) -> None:
        now = datetime.utcnow().isoformat()
        async with get_db() as db:
            await db.execute(
                "UPDATE users SET is_active = 0, updated_at = ? WHERE telegram_id = ?",
                (now, telegram_id),
            )
            await db.commit()


class SubscriptionRepository:
    @staticmethod
    async def add(user_id: int, category: str) -> Subscription:
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO subscriptions (user_id, category) VALUES (?, ?)",
                (user_id, category),
            )
            await db.commit()
            return Subscription(id=cursor.lastrowid, user_id=user_id, category=category)

    @staticmethod
    async def get_by_user(user_id: int) -> list[Subscription]:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM subscriptions WHERE user_id = ?", (user_id,))
            rows = await cursor.fetchall()
            return [
                Subscription(id=row["id"], user_id=row["user_id"], category=row["category"])
                for row in rows
            ]

    @staticmethod
    async def remove_all(user_id: int) -> None:
        async with get_db() as db:
            await db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            await db.commit()

    @staticmethod
    async def get_subscriber_ids_by_category(category: str) -> list[int]:
        async with get_db() as db:
            cursor = await db.execute(
                """SELECT DISTINCT user_id FROM subscriptions
                   WHERE category = ? OR category = 'all'""",
                (category,),
            )
            rows = await cursor.fetchall()
            return [row["user_id"] for row in rows]


class HolidayRepository:
    @staticmethod
    async def get_by_date(holiday_date: date) -> list[Holiday]:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM holidays_cache WHERE date = ?",
                (holiday_date.isoformat(),),
            )
            rows = await cursor.fetchall()
            return [
                Holiday(
                    id=row["id"],
                    date=date.fromisoformat(row["date"]),
                    name=row["name"],
                    category=row["category"],
                    description=row["description"],
                    external_id=row["external_id"],
                )
                for row in rows
            ]

    @staticmethod
    async def get_by_date_and_category(holiday_date: date, category: str) -> list[Holiday]:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM holidays_cache WHERE date = ? AND category = ?",
                (holiday_date.isoformat(), category),
            )
            rows = await cursor.fetchall()
            return [
                Holiday(
                    id=row["id"],
                    date=date.fromisoformat(row["date"]),
                    name=row["name"],
                    category=row["category"],
                    description=row["description"],
                    external_id=row["external_id"],
                )
                for row in rows
            ]

    @staticmethod
    async def bulk_insert(holidays: list[Holiday]) -> None:
        async with get_db() as db:
            for h in holidays:
                await db.execute(
                    "INSERT OR IGNORE INTO holidays_cache "
                    "(date, name, category, description, external_id) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (h.date.isoformat(), h.name, h.category, h.description, h.external_id),
                )
            await db.commit()

    @staticmethod
    async def has_cache_for_date(holiday_date: date) -> bool:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT 1 FROM holidays_cache WHERE date = ? LIMIT 1",
                (holiday_date.isoformat(),),
            )
            return await cursor.fetchone() is not None


class NotificationLogRepository:
    @staticmethod
    async def add(user_id: int, holiday_id: int) -> NotificationLog:
        now = datetime.utcnow().isoformat()
        async with get_db() as db:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO notifications_log (user_id, holiday_id, sent_at) "
                "VALUES (?, ?, ?)",
                (user_id, holiday_id, now),
            )
            await db.commit()
            return NotificationLog(
                id=cursor.lastrowid,
                user_id=user_id,
                holiday_id=holiday_id,
                sent_at=datetime.fromisoformat(now),
            )

    @staticmethod
    async def was_sent(user_id: int, holiday_id: int) -> bool:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT 1 FROM notifications_log WHERE user_id = ? AND holiday_id = ?",
                (user_id, holiday_id),
            )
            return await cursor.fetchone() is not None
