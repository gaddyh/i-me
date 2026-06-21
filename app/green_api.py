import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger("greenapi-bot")


async def send_whatsapp_message(chat_id: str, message: str) -> dict[str, Any]:
    url = (
        f"{settings.green_api_base_url}"
        f"/waInstance{settings.green_api_id_instance}"
        f"/sendMessage/"
        f"{settings.green_api_token_instance}"
    )

    payload = {
        "chatId": chat_id,
        "message": message,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)

        if response.status_code >= 400:
            logger.error(
                "Green API sendMessage failed status=%s chat_id=%s body=%s",
                response.status_code,
                chat_id,
                response.text,
            )

        response.raise_for_status()
        return response.json()