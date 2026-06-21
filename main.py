import logging
from typing import Any

from fastapi import FastAPI, Request

from app.config import settings
from app.security import verify_green_api_authorization
from app.webhook_handler import handle_green_api_webhook

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("greenapi-bot")

app = FastAPI(title="Green API WhatsApp Bot")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/green-api")
async def green_api_webhook(request: Request) -> dict[str, Any]:
    verify_green_api_authorization(request)

    payload = await request.json()

    logger.info(
        "Webhook received type=%s idMessage=%s",
        payload.get("typeWebhook"),
        payload.get("idMessage"),
    )

    return await handle_green_api_webhook(payload)