import logging
from typing import Any

from app.agent.main import process_message
from app.audio import handle_audio_message
from app.config import settings
from app.green_api import send_whatsapp_message
from app.storage.reminder_store import ReminderStore
from app.webhook import (
    extract_extended_text_message,
    extract_text_message,
    get_chat_id,
    get_chat_name,
    get_message_data,
    get_message_id,
    get_message_type,
    get_type_webhook,
)

logger = logging.getLogger("greenapi-bot")

_reminder_store = ReminderStore()


async def handle_green_api_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    type_webhook = get_type_webhook(payload)

    chat_id = get_chat_id(payload)
    chat_name = get_chat_name(payload)

    if not chat_id:
        return {"ok": False, "error": "Missing senderData.chatId"}

    logger.info("Incoming message from chat_id=%s, chat_name=%s", chat_id, chat_name)

    if chat_name not in settings.allowed_chat_ids:
        logger.info("Ignoring message from non-allowed chat_id=%s", chat_id)
        return {
            "ok": True,
            "ignored": "chat_not_allowed",
            "chatId": chat_id,
            "chatName": chat_name,
        }

    message_id = get_message_id(payload)

    if message_id and await _reminder_store.is_seen(message_id):
        return {"ok": True, "duplicate": True}

    if message_id:
        await _reminder_store.mark_seen(message_id)

    message_data = get_message_data(payload)
    type_message = get_message_type(payload)

    try:
        if type_message == "textMessage":
            text = extract_text_message(message_data)
            response = await process_message(chat_id, text)
            await send_whatsapp_message(chat_id, response)
            return {"ok": True, "handled": "textMessage"}

        if type_message == "extendedTextMessage":
            text = extract_extended_text_message(message_data)
            response = await process_message(chat_id, text)
            await send_whatsapp_message(chat_id, response)
            return {"ok": True, "handled": "extendedTextMessage"}

        if type_message == "audioMessage":
            await send_whatsapp_message(chat_id, "Got your audio. Transcribing...")
            transcript = await handle_audio_message(message_data)
            response = await process_message(chat_id, transcript)
            await send_whatsapp_message(chat_id, response)
            return {"ok": True, "handled": "audioMessage"}

        logger.info("Ignoring unsupported message type: %s", type_message)
        return {"ok": True, "ignored_message_type": type_message}

    except Exception as e:
        logger.exception("Failed handling webhook")
        await safe_send_error_message(chat_id, e)
        return {"ok": False, "error": str(e)}


async def safe_send_error_message(chat_id: str, error: Exception) -> None:
    try:
        await send_whatsapp_message(chat_id, f"Error while handling message: {error}")
    except Exception:
        logger.exception("Failed sending error message to chat_id=%s", chat_id)