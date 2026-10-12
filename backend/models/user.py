from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"
EXTERNAL_ACCOUNT_KEYS = {"steam", "youtube", "twitch", "kick", "playstation", "xbox", "epic", "discord"}
MAX_AVATAR_CHARS = 3_000_000  # ~2 MB image encoded in base64


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=3, max_length=30, pattern=USERNAME_PATTERN)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserProfile(BaseModel):
    id: str
    # Only returned for the authenticated user; hidden (null) for other users.
    email: Optional[str] = None
    username: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
    favorite_games: List[str] = []
    external_accounts: Dict[str, str] = {}
    created_at: datetime


class UserUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    username: Optional[str] = Field(default=None, min_length=3, max_length=30, pattern=USERNAME_PATTERN)
    avatar: Optional[str] = Field(default=None, max_length=MAX_AVATAR_CHARS)
    bio: Optional[str] = Field(default=None, max_length=300)
    favorite_games: Optional[List[str]] = Field(default=None, max_length=50)
    external_accounts: Optional[Dict[str, str]] = None

    @field_validator("avatar")
    @classmethod
    def avatar_must_be_image(cls, v):
        if v and not (v.startswith("data:image/") or v.startswith("https://")):
            raise ValueError("Avatar must be an image data URI or https URL")
        return v

    @field_validator("favorite_games")
    @classmethod
    def games_length(cls, v):
        if v and any(len(g) > 60 for g in v):
            raise ValueError("Game names must be at most 60 characters")
        return v

    @field_validator("external_accounts")
    @classmethod
    def external_accounts_valid(cls, v):
        if v is None:
            return v
        unknown = set(v) - EXTERNAL_ACCOUNT_KEYS
        if unknown:
            raise ValueError(f"Unsupported accounts: {', '.join(sorted(unknown))}")
        if any(len(val) > 200 for val in v.values()):
            raise ValueError("Account links must be at most 200 characters")
        return {k: val.strip() for k, val in v.items()}


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserProfile


def to_profile(user: dict, include_email: bool = False) -> UserProfile:
    return UserProfile(
        id=str(user["_id"]),
        email=user["email"] if include_email else None,
        username=user["username"],
        avatar=user.get("avatar"),
        bio=user.get("bio"),
        favorite_games=user.get("favorite_games", []),
        external_accounts=user.get("external_accounts", {}),
        created_at=user["created_at"],
    )
