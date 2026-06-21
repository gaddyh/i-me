from typing import Any


def get_type_webhook(payload: dict[str, Any]) -> str | None:
    return payload.get("typeWebhook")


def get_message_id(payload: dict[str, Any]) -> str | None:
    return payload.get("idMessage")


def get_chat_id(payload: dict[str, Any]) -> str | None:
    sender_data = payload.get("senderData") or {}
    return sender_data.get("chatId")


def get_message_data(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("messageData") or {}


def get_message_type(payload: dict[str, Any]) -> str | None:
    return get_message_data(payload).get("typeMessage")


def extract_text_message(message_data: dict[str, Any]) -> str:
    return (
        (message_data.get("textMessageData") or {})
        .get("textMessage", "")
        .strip()
    )


def extract_extended_text_message(message_data: dict[str, Any]) -> str:
    return (
        (message_data.get("extendedTextMessageData") or {})
        .get("text", "")
        .strip()
    )