from typing import Any


def create_reminder(
    reminder_text: str,
    remind_date: str,
    remind_time: str,
    timezone: str = "Asia/Jerusalem",
) -> dict[str, Any]:
    """
    Create a reminder.

    Args:
        reminder_text: What to remind the user about.
        remind_date: Reminder date in YYYY-MM-DD.
        remind_time: Reminder time in HH:MM 24-hour format.
        timezone: IANA timezone. Default Asia/Jerusalem.
    """
    return {
        "return_value": (
            f"Reminder set: {reminder_text} on {remind_date} at {remind_time}"
        ),
        "reminder": {
            "reminder_text": reminder_text,
            "remind_date": remind_date,
            "remind_time": remind_time,
            "timezone": timezone,
        },
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