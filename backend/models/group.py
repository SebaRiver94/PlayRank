from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GroupCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=60)
    icon: Optional[str] = Field(default=None, max_length=16)
    description: Optional[str] = Field(default=None, max_length=500)


class GroupUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: Optional[str] = Field(default=None, min_length=1, max_length=60)
    icon: Optional[str] = Field(default=None, max_length=16)
    description: Optional[str] = Field(default=None, max_length=500)


class Group(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    description: Optional[str] = None
    owner_id: str
    members: List[str] = []
    created_at: datetime


class GameTypeCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=60)
    icon: Optional[str] = Field(default=None, max_length=16)


class GameType(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    group_id: str
    created_at: datetime


def to_group(g: dict) -> Group:
    return Group(
        id=str(g["_id"]),
        name=g["name"],
        icon=g.get("icon"),
        description=g.get("description"),
        owner_id=g["owner_id"],
        members=g["members"],
        created_at=g["created_at"],
    )


def to_game_type(gt: dict) -> GameType:
    return GameType(
        id=str(gt["_id"]),
        name=gt["name"],
        icon=gt.get("icon"),
        group_id=gt["group_id"],
        created_at=gt["created_at"],
    )
