from datetime import datetime
from typing import Optional

from pydantic import BaseModel

MAX_MESSAGE_LENGTH = 1000


class Message(BaseModel):
    id: str
    group_id: str
    user_id: str
    username: str
    avatar: Optional[str] = None
    content: str
    created_at: datetime


class Activity(BaseModel):
    id: str
    group_id: str
    user_id: str
    username: str
    activity_type: str
    description: str
    created_at: datetime
