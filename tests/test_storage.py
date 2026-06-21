"""Unit tests for ReminderStore and ConversationStore."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio

from app.storage.conversation_store import ConversationStore
from app.storage.models import Reminder
from app.storage.reminder_store import ReminderStore, init_db


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest_asyncio.fixture
async def store(tmp_db: Path) -> ReminderStore:
    await init_db(tmp_db)
    return ReminderStore(path=tmp_db)


@pytest.mark.asyncio
async def test_create_and_get_due(store: ReminderStore):
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    reminder = Reminder(chat_id="user1", text="Test reminder", target_time=past)

    await store.create(reminder)
    due = await store.get_due()

    assert len(due) == 1
    assert due[0].id == reminder.id
    assert due[0].text == "Test reminder"


@pytest.mark.asyncio
async def test_future_reminder_not_due(store: ReminderStore):
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    reminder = Reminder(chat_id="user1", text="Future", target_time=future)

    await store.create(reminder)
    due = await store.get_due()

    assert len(due) == 0


@pytest.mark.asyncio
async def test_mark_sent(store: ReminderStore):
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    reminder = Reminder(chat_id="user1", text="Send me", target_time=past)

    await store.create(reminder)
    await store.mark_sent(reminder.id)
    due = await store.get_due()

    assert len(due) == 0


@pytest.mark.asyncio
async def test_seen_message_dedup(store: ReminderStore):
    msg_id = "msg-abc-123"

    assert not await store.is_seen(msg_id)
    await store.mark_seen(msg_id)
    assert await store.is_seen(msg_id)

    await store.mark_seen(msg_id)
    assert await store.is_seen(msg_id)


class TestConversationStore:
    def test_append_and_get(self):
        cs = ConversationStore()
        cs.append("chat1", "user", "Hello")
        cs.append("chat1", "assistant", "Hi there")

        history = cs.get("chat1")
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there"}

    def test_max_history_truncation(self):
        cs = ConversationStore(max_history=3)
        for i in range(5):
            cs.append("chat1", "user", f"msg{i}")

        history = cs.get("chat1")
        assert len(history) == 3
        assert history[0]["content"] == "msg2"

    def test_clear(self):
        cs = ConversationStore()
        cs.append("chat1", "user", "Hello")
        cs.clear("chat1")
        assert cs.get("chat1") == []

    def test_to_json_empty(self):
        cs = ConversationStore()
        assert cs.to_json("unknown") == "[]"

    def test_independent_chats(self):
        cs = ConversationStore()
        cs.append("chat1", "user", "msg from chat1")
        cs.append("chat2", "user", "msg from chat2")

        assert len(cs.get("chat1")) == 1
        assert len(cs.get("chat2")) == 1
        assert cs.get("chat1")[0]["content"] == "msg from chat1"
