import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.green_api import send_whatsapp_message
from app.storage.reminder_store import ReminderStore

logger = logging.getLogger("greenapi-bot")

_reminder_store = ReminderStore()
_scheduler = AsyncIOScheduler()


async def _fire_due_reminders() -> None:
    reminders = await _reminder_store.get_due()

    logger.debug("Scheduler tick: %d due reminder(s)", len(reminders))

    if not reminders:
        return

    logger.info("Firing %d due reminder(s)", len(reminders))

    for reminder in reminders:
        try:
            await send_whatsapp_message(reminder.chat_id, f"Reminder: {reminder.text}")
            await _reminder_store.mark_sent(reminder.id)
            logger.info("Reminder sent id=%s chat_id=%s", reminder.id, reminder.chat_id)
        except Exception:
            await _reminder_store.mark_failed(reminder.id)
            logger.exception(
                "Failed to send reminder id=%s chat_id=%s", reminder.id, reminder.chat_id
            )


def start_scheduler() -> None:
    _scheduler.add_job(
        _fire_due_reminders,
        trigger="interval",
        seconds=60,
        id="fire_due_reminders",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Reminder scheduler started (60s interval)")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Reminder scheduler stopped")
