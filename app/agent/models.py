

from pydantic import BaseModel
from datetime import datetime


class Reminder(BaseModel):
    chat_id: str
    text: str
    target_time: datetime

    created_at: datetime
    updated_at: datetime
    