from fastapi import APIRouter, Depends, HTTPException

from core.db import db
from core.security import get_current_user
from core.utils import parse_oid
from models.user import UserProfile, UserUpdate, to_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.put("/profile", response_model=UserProfile)
async def update_profile(user_update: UserUpdate, current_user: dict = Depends(get_current_user)):
    update_data = user_update.model_dump(exclude_none=True)

    if "username" in update_data:
        existing = await db.users.find_one({
            "username": update_data["username"],
            "_id": {"$ne": current_user["_id"]},
        })
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")

    if update_data:
        await db.users.update_one({"_id": current_user["_id"]}, {"$set": update_data})

    updated_user = await db.users.find_one({"_id": current_user["_id"]})
    return to_profile(updated_user, include_email=True)


@router.get("/{user_id}", response_model=UserProfile)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"_id": parse_oid(user_id, "User")})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return to_profile(user, include_email=user["_id"] == current_user["_id"])
