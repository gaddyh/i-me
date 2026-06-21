import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.storage.models import Reminder

logger = logging.getLogger("greenapi-bot")

_DB_PATH = Path("data/reminders.db")


def _get_db(path: Path = _DB_PATH) -> aiosqlite.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = aiosqlite.connect(str(path))
    return conn


async def init_db(path: Path = _DB_PATH) -> None:
    async with _get_db(path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id          TEXT PRIMARY KEY,
                chat_id     TEXT NOT NULL,
                text        TEXT NOT NULL,
                target_time TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_messages (
                message_id TEXT PRIMARY KEY,
                seen_at    TEXT NOT NULL
            )
            """
        )
        await db.commit()


class ReminderStore:
    def __init__(self, path: Path = _DB_PATH) -> None:
        self._path = path

    async def create(self, reminder: Reminder) -> Reminder:
        async with _get_db(self._path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                """
                INSERT INTO reminders (id, chat_id, text, target_time, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reminder.id,
                    reminder.chat_id,
                    reminder.text,
                    reminder.target_time.isoformat(),
                    reminder.status,
                    reminder.created_at.isoformat(),
                    reminder.updated_at.isoformat(),
                ),
            )
            await db.commit()
        logger.info("Reminder created id=%s chat_id=%s", reminder.id, reminder.chat_id)
        return reminder

    async def get_due(self, now: datetime | None = None) -> list[Reminder]:
        if now is None:
            now = datetime.now(timezone.utc)
        async with _get_db(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM reminders
                WHERE status = 'pending' AND target_time <= ?
                ORDER BY target_time ASC
                """,
                (now.isoformat(),),
            )
            rows = await cursor.fetchall()
        return [_row_to_reminder(row) for row in rows]

    async def mark_sent(self, reminder_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with _get_db(self._path) as db:
            await db.execute(
                "UPDATE reminders SET status = 'sent', updated_at = ? WHERE id = ?",
                (now, reminder_id),
            )
            await db.commit()

    async def mark_failed(self, reminder_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with _get_db(self._path) as db:
            await db.execute(
                "UPDATE reminders SET status = 'failed', updated_at = ? WHERE id = ?",
                (now, reminder_id),
            )
            await db.commit()

    async def is_seen(self, message_id: str) -> bool:
        async with _get_db(self._path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT 1 FROM seen_messages WHERE message_id = ?",
                (message_id,),
            )
            return await cursor.fetchone() is not None

    async def mark_seen(self, message_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with _get_db(self._path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO seen_messages (message_id, seen_at) VALUES (?, ?)",
                (message_id, now),
            )
            await db.commit()


def _row_to_reminder(row: aiosqlite.Row) -> Reminder:
    return Reminder(
        id=row["id"],
        chat_id=row["chat_id"],
        text=row["text"],
        target_time=datetime.fromisoformat(row["target_time"]),
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
