from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from core.db import db
from core.security import get_current_user
from core.themes import build_profile_write, normalize_theme, theme_version_of
from core.utils import parse_oid
from models.user import UserProfile, UserUpdate, to_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.put("/profile", response_model=UserProfile)
async def update_profile(user_update: UserUpdate, current_user: dict = Depends(get_current_user)):
    update_data = user_update.model_dump(exclude_none=True)
    # The theme is handled separately (versioned, compare-and-set); never $set it blindly.
    theme = update_data.pop("theme", None)
    base_version = update_data.pop("theme_base_version", None)

    if "username" in update_data:
        existing = await db.users.find_one({
            "username": update_data["username"],
            "_id": {"$ne": current_user["_id"]},
        })
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")

    write = build_profile_write(current_user, update_data, theme, base_version, datetime.utcnow())
    if write:
        extra_query, update = write
        try:
            result = await db.users.update_one({"_id": current_user["_id"], **extra_query}, update)
        except DuplicateKeyError:  # lost a race on the unique username index
            raise HTTPException(status_code=400, detail="Username already taken")
        if result.matched_count == 0:
            latest = await db.users.find_one({"_id": current_user["_id"]})
            if not latest or not extra_query:
                raise HTTPException(status_code=404, detail="User not found")
            # Another device changed the theme since this client last synced. Nothing was
            # written (the whole update is atomic); the client should adopt the current value.
            raise HTTPException(status_code=409, detail={
                "code": "theme_conflict",
                "message": "Theme was changed from another device",
                "theme": normalize_theme(latest.get("theme")),
                "theme_version": theme_version_of(latest),
            })

    updated_user = await db.users.find_one({"_id": current_user["_id"]})
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_profile(updated_user, include_email=True)


@router.get("/{user_id}", response_model=UserProfile)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"_id": parse_oid(user_id, "User")})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_profile(user, include_email=user["_id"] == current_user["_id"])
