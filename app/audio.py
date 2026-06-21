import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.config import settings

openai_client = AsyncOpenAI()

SUPPORTED_TRANSCRIPTION_EXTS = {
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".wav",
    ".webm",
}


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
            model=settings.openai_transcribe_model,
            file=audio_file,
        )

    return transcription.text.strip()


def suffix_from_mime(mime_type: str) -> str:
    normalized = mime_type.split(";")[0].strip().lower()

    mapping = {
        "audio/ogg": ".ogg",
        "audio/opus": ".ogg",
        "audio/mpeg": ".mpeg",
        "audio/mpga": ".mpga",
        "audio/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
    }

    return mapping.get(normalized, ".bin")