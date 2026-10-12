from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends

from core.db import db
from core.security import get_current_user
from models.match import LeaderboardEntry, UserStats
from services.permissions import get_member_group

router = APIRouter(prefix="/groups/{group_id}", tags=["rankings"])


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(group_id: str, current_user: dict = Depends(get_current_user)):
    await get_member_group(group_id, current_user)
    stats = await db.stats.find({"group_id": group_id}).sort("wins", -1).limit(50).to_list(50)

    user_ids = [ObjectId(s["user_id"]) for s in stats if ObjectId.is_valid(s["user_id"])]
    users = {str(u["_id"]): u for u in await db.users.find({"_id": {"$in": user_ids}}).to_list(len(user_ids))}

    return [
        LeaderboardEntry(
            user_id=s["user_id"],
            username=users[s["user_id"]]["username"],
            avatar=users[s["user_id"]].get("avatar"),
            total_matches=s["total_matches"],
            wins=s["wins"],
            losses=s["losses"],
            win_rate=s["win_rate"],
            current_streak=s["current_streak"],
            streak_type=s["streak_type"],
        )
        for s in stats if s["user_id"] in users
    ]


@router.get("/stats/{user_id}", response_model=UserStats)
async def get_user_stats(group_id: str, user_id: str, current_user: dict = Depends(get_current_user)):
    await get_member_group(group_id, current_user)
    stats = await db.stats.find_one({"user_id": user_id, "group_id": group_id})
    if not stats:
        return UserStats(user_id=user_id, group_id=group_id)
    return UserStats(**stats)
