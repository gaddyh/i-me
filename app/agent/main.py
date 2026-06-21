import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.agent.dspy_config import configure_dspy_once
from app.agent.single_turn_agent import WhatsAppSingleTurnAgent

logger = logging.getLogger("greenapi-bot")

_agent: WhatsAppSingleTurnAgent | None = None


def get_agent() -> WhatsAppSingleTurnAgent:
    global _agent

    configure_dspy_once()

    if _agent is None:
        _agent = WhatsAppSingleTurnAgent(max_steps=1)

    return _agent


async def process_message(chat_id: str, text: str) -> str:
    clean_text = text.strip()

    if not clean_text:
        return "I got an empty message."

    timezone = "Asia/Jerusalem"
    now = datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d %H:%M:%S")

    agent = get_agent()

    try:
        prediction = await asyncio.to_thread(
            agent,
            user_input=clean_text,
            now=now,
            timezone=timezone,
        )

        logger.info(
            "Agent decision chat_id=%s selected_fn=%s args=%s",
            chat_id,
            prediction.selected_fn,
            prediction.args,
        )

        return prediction.response.strip()

    except Exception as e:
        logger.exception("Agent failed")
        return f"Sorry, I had trouble processing that. Error: {e}"