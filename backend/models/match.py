from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MatchCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    game_type_id: str
    group_id: str
    date: datetime
    players: List[str] = Field(min_length=2, max_length=50)
    winner_ids: List[str] = Field(min_length=1, max_length=50)
    score: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def check_players(self):
        if len(set(self.players)) != len(self.players):
            raise ValueError("Players must be unique")
        if len(set(self.winner_ids)) != len(self.winner_ids):
            raise ValueError("Winners must be unique")
        if not set(self.winner_ids).issubset(self.players):
            raise ValueError("Winners must be among the players")
        return self


class Match(BaseModel):
    id: str
    game_type_id: str
    group_id: str
    date: datetime
    players: List[str]
    winner_ids: List[str]
    score: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: datetime


class LeaderboardEntry(BaseModel):
    user_id: str
    username: str
    avatar: Optional[str] = None
    total_matches: int
    wins: int
    losses: int
    win_rate: float
    current_streak: int
    streak_type: str  # "win", "loss" or "none"


class UserStats(BaseModel):
    user_id: str
    group_id: str
    total_matches: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    current_streak: int = 0
    streak_type: str = "none"
    best_win_streak: int = 0


def to_match(m: dict) -> Match:
    return Match(
        id=str(m["_id"]),
        game_type_id=m["game_type_id"],
        group_id=m["group_id"],
        date=m["date"],
        players=m["players"],
        winner_ids=m["winner_ids"],
        score=m.get("score"),
        notes=m.get("notes"),
        created_by=m["created_by"],
        created_at=m["created_at"],
    )
