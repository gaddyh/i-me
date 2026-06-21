import asyncio
import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.storage.models import Reminder
from app.storage.reminder_store import ReminderStore, init_db

logger = logging.getLogger("greenapi-bot")

_reminder_store = ReminderStore()


def create_reminder(
    reminder_text: str,
    remind_date: str,
    remind_time: str,
    timezone: str = "Asia/Jerusalem",
    chat_id: str = "",
) -> dict[str, Any]:
    """
    Create a reminder.

    Args:
        reminder_text: What to remind the user about.
        remind_date: Reminder date in YYYY-MM-DD.
        remind_time: Reminder time in HH:MM 24-hour format.
        timezone: IANA timezone. Default Asia/Jerusalem.
        chat_id: WhatsApp chat ID for delivery. Injected by the agent framework.
    """
    try:
        tz = ZoneInfo(timezone)
        target_time = datetime.strptime(
            f"{remind_date} {remind_time}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=tz)
    except Exception as exc:
        logger.warning("create_reminder: bad date/time input: %s", exc)
        return {
            "return_value": (
                f"Reminder set: {reminder_text} on {remind_date} at {remind_time}"
            ),
        }

    reminder = Reminder(
        chat_id=chat_id,
        text=reminder_text,
        target_time=target_time,
    )

    async def _persist():
        await init_db()
        await _reminder_store.create(reminder)

    asyncio.run(_persist())

    return {
        "return_value": (
            f"Reminder set: {reminder_text} on {remind_date} at {remind_time}"
        ),
        "reminder_id": reminder.id,
    }


def ask_clarification(
    question: str,
    missing_fields: list[str],
) -> dict[str, Any]:
    """
    Ask the user for missing information.

    Args:
        question: Short clarification question to send to the user.
        missing_fields: Missing required fields. Use: reminder_text, remind_date, remind_time.
    """
    return {
        "return_value": question,
        "missing_fields": missing_fields,
    }


def finish(response: str) -> dict[str, Any]:
    """
    Finish without calling a domain action.

    Args:
        response: Short final answer to the user.
    """
    return {
        "return_value": response,
    }


AVAILABLE_FUNCTIONS = {
    "create_reminder": create_reminder,
    "ask_clarification": ask_clarification,
    "finish": finish,
}