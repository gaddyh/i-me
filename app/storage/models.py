import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Reminder(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chat_id: str
    text: str
    target_time: datetime
    status: Literal["pending", "sent", "failed"] = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
