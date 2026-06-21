import os
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from openai import AsyncOpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("greenapi-bot")

app = FastAPI(title="Green API WhatsApp Echo Bot")

openai_client = AsyncOpenAI()

GREEN_API_BASE_URL = os.getenv("GREEN_API_BASE_URL", "https://api.green-api.com").rstrip("/")
GREEN_API_ID_INSTANCE = os.getenv("GREEN_API_ID_INSTANCE")
GREEN_API_TOKEN_INSTANCE = os.getenv("GREEN_API_TOKEN_INSTANCE")
OPENAI_TRANSCRIBE_MODEL = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-transcribe")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

if not WEBHOOK_SECRET:
    raise RuntimeError("Missing WEBHOOK_SECRET")

EXPECTED_AUTHORIZATION_HEADER = f"Bearer {WEBHOOK_SECRET}"

ALLOWED_CHAT_IDS_RAW = os.getenv("ALLOWED_CHAT_IDS", "")

ALLOWED_CHAT_IDS = {
    chat_id.strip()
    for chat_id in ALLOWED_CHAT_IDS_RAW.split(",")
    if chat_id.strip()
}

if not ALLOWED_CHAT_IDS:
    logger.warning(
        "ALLOWED_CHAT_IDS is empty. Bot will ignore all incoming messages."
    )

if not GREEN_API_ID_INSTANCE:
    raise RuntimeError("Missing GREEN_API_ID_INSTANCE")

if not GREEN_API_TOKEN_INSTANCE:
    raise RuntimeError("Missing GREEN_API_TOKEN_INSTANCE")


SUPPORTED_TRANSCRIPTION_EXTS = {
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".wav",
    ".webm",
}


_seen_message_ids: set[str] = set()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

def verify_green_api_authorization(request: Request) -> None:
    authorization = request.headers.get("authorization")

    if authorization != EXPECTED_AUTHORIZATION_HEADER:
        logger.warning("Rejected webhook with invalid Authorization header")
        raise HTTPException(status_code=403, detail="Invalid webhook authorization")

@app.post("/webhooks/green-api")
async def green_api_webhook(request: Request) -> dict[str, Any]:
    print("Webhook received")
    verify_green_api_authorization(request)

    payload = await request.json()
    logger.info("Webhook received: %s", payload)

    message_id = payload.get("idMessage")
    if message_id and message_id in _seen_message_ids:
        return {"ok": True, "duplicate": True}

    if message_id:
        _seen_message_ids.add(message_id)

    sender_data = payload.get("senderData") or {}
    chat_id = sender_data.get("chatId")

    if not chat_id:
        return {"ok": False, "error": "Missing senderData.chatId"}

    logger.info("Incoming message from chat_id=%s", chat_id)

    if chat_id not in ALLOWED_CHAT_IDS:
        logger.info("Ignoring message from non-allowed chat_id=%s", chat_id)
        return {
            "ok": True,
            "ignored": "chat_not_allowed",
            "chatId": chat_id,
        }

    message_data = payload.get("messageData") or {}
    type_message = message_data.get("typeMessage")

    try:
        if type_message == "textMessage":
            text = extract_text_message(message_data)
            await send_whatsapp_message(chat_id, f"Echo: {text}")
            return {"ok": True, "handled": "textMessage"}

        if type_message == "extendedTextMessage":
            text = extract_extended_text_message(message_data)
            await send_whatsapp_message(chat_id, f"Echo: {text}")
            return {"ok": True, "handled": "extendedTextMessage"}

        if type_message == "audioMessage":
            await send_whatsapp_message(chat_id, "Got your audio. Transcribing...")
            transcript = await handle_audio_message(message_data)
            await send_whatsapp_message(chat_id, f"Transcript:\n{transcript}")
            return {"ok": True, "handled": "audioMessage"}

        logger.info("Ignoring unsupported message type: %s", type_message)
        return {"ok": True, "ignored_message_type": type_message}

    except Exception as e:
        logger.exception("Failed handling webhook")
        await send_whatsapp_message(chat_id, f"Error while handling message: {e}")
        return {"ok": False, "error": str(e)}


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


async def handle_audio_message(message_data: dict[str, Any]) -> str:
    file_data = message_data.get("fileMessageData") or {}

    download_url = file_data.get("downloadUrl")
    if not download_url:
        raise ValueError("Missing fileMessageData.downloadUrl")

    file_name = file_data.get("fileName") or "voice-message"
    suffix = Path(file_name).suffix or suffix_from_mime(file_data.get("mimeType", ""))

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / f"audio{suffix}"

        await download_file(download_url, raw_path)

        transcribable_path = ensure_transcribable_audio(raw_path)

        return await transcribe_audio(transcribable_path)


async def download_file(url: str, target_path: Path) -> None:
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        target_path.write_bytes(response.content)


def ensure_transcribable_audio(path: Path) -> Path:
    """
    OpenAI transcription file upload supports formats such as:
    mp3, mp4, mpeg, mpga, m4a, wav, webm.
    WhatsApp voice notes often arrive as ogg/opus, so we convert unsupported
    formats to wav using ffmpeg.
    """
    if path.suffix.lower() in SUPPORTED_TRANSCRIPTION_EXTS:
        return path

    converted = path.with_suffix(".wav")

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-ar",
            "16000",
            "-ac",
            "1",
            str(converted),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    return converted


async def transcribe_audio(path: Path) -> str:
    with path.open("rb") as audio_file:
        transcription = await openai_client.audio.transcriptions.create(
            model=OPENAI_TRANSCRIBE_MODEL,
            file=audio_file,
        )

    return transcription.text.strip()


async def send_whatsapp_message(chat_id: str, message: str) -> dict[str, Any]:
    url = (
        f"{GREEN_API_BASE_URL}"
        f"/waInstance{GREEN_API_ID_INSTANCE}"
        f"/sendMessage/"
        f"{GREEN_API_TOKEN_INSTANCE}"
    )

    payload = {
        "chatId": chat_id,
        "message": message,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def suffix_from_mime(mime_type: str) -> str:
    mapping = {
        "audio/ogg": ".ogg",
        "audio/opus": ".ogg",
        "audio/mpeg": ".mpeg",
        "audio/mpga": ".mpga",
        "audio/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
    }
    return mapping.get(mime_type.lower(), ".bin")