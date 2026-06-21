import json
import logging
from collections import defaultdict

logger = logging.getLogger("greenapi-bot")

_MAX_HISTORY = 10


class ConversationStore:
    """In-memory per-user conversation history. Swap for a DB-backed version later."""

    def __init__(self, max_history: int = _MAX_HISTORY) -> None:
        self._max_history = max_history
        self._store: dict[str, list[dict]] = defaultdict(list)

    def get(self, chat_id: str) -> list[dict]:
        return list(self._store[chat_id])

    def append(self, chat_id: str, role: str, content: str) -> None:
        history = self._store[chat_id]
        history.append({"role": role, "content": content})
        if len(history) > self._max_history:
            self._store[chat_id] = history[-self._max_history :]

    def clear(self, chat_id: str) -> None:
        self._store.pop(chat_id, None)

    def to_json(self, chat_id: str) -> str:
        return json.dumps(self.get(chat_id), ensure_ascii=False)


conversation_store = ConversationStore()
