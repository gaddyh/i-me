"""Unit tests for agent tool functions."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agent.tools import ask_clarification, finish


def test_finish_returns_response():
    result = finish(response="All done!")
    assert result["return_value"] == "All done!"


def test_ask_clarification_returns_question():
    result = ask_clarification(
        question="What time?",
        missing_fields=["remind_time"],
    )
    assert result["return_value"] == "What time?"
    assert result["missing_fields"] == ["remind_time"]


def test_ask_clarification_multiple_fields():
    result = ask_clarification(
        question="Missing info",
        missing_fields=["remind_date", "remind_time"],
    )
    assert "remind_date" in result["missing_fields"]
    assert "remind_time" in result["missing_fields"]


@patch("app.agent.tools.asyncio.run")
@patch("app.agent.tools._reminder_store")
def test_create_reminder_persists(mock_store, mock_run):
    mock_store.create = AsyncMock()

    from app.agent.tools import create_reminder

    result = create_reminder(
        reminder_text="Buy milk",
        remind_date="2025-12-01",
        remind_time="09:00",
        timezone="Asia/Jerusalem",
        chat_id="972501234567@c.us",
    )

    assert "return_value" in result
    assert "Buy milk" in result["return_value"]
    assert "reminder_id" in result
    mock_run.assert_called_once()


@patch("app.agent.tools.asyncio.run")
@patch("app.agent.tools._reminder_store")
def test_create_reminder_bad_date_falls_back(mock_store, mock_run):
    from app.agent.tools import create_reminder

    result = create_reminder(
        reminder_text="Buy milk",
        remind_date="not-a-date",
        remind_time="bad",
        timezone="Asia/Jerusalem",
    )

    assert "return_value" in result
    mock_run.assert_not_called()
