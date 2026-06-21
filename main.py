import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request

from app.config import settings
from app.scheduler import start_scheduler, stop_scheduler
from app.security import verify_green_api_authorization
from app.storage.reminder_store import init_db
from app.webhook_handler import handle_green_api_webhook

_log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(level=_log_level)
logger = logging.getLogger("greenapi-bot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Green API WhatsApp Bot", lifespan=lifespan)


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