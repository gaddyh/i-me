import asyncio
import logging

from app.agent.dspy_config import configure_dspy_once
from app.agent.react_agent import WhatsAppReActAgent

logger = logging.getLogger("greenapi-bot")

_agent: WhatsAppReActAgent | None = None


def get_agent() -> WhatsAppReActAgent:
    global _agent

    configure_dspy_once()

    if _agent is None:
        _agent = WhatsAppReActAgent()

    return _agent


async def process_message(chat_id: str, text: str) -> str:
    clean_text = text.strip()

    if not clean_text:
        return "I got an empty message."

    agent = get_agent()

    try:
        prediction = await asyncio.to_thread(
            agent,
            user_input=clean_text,
        )
        return prediction.response.strip()

    except Exception as e:
        logger.exception("Agent failed")
        return f"Sorry, I had trouble processing that. Error: {e}"