from typing import List

from fastapi import APIRouter, Depends, Query

from core.db import db
from core.security import get_current_user
from models.social import Activity, Message
from services.permissions import get_member_group

router = APIRouter(prefix="/groups/{group_id}", tags=["social"])


@router.get("/messages", response_model=List[Message])
async def get_messages(group_id: str, limit: int = Query(50, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    await get_member_group(group_id, current_user)
    messages = await db.messages.find({"group_id": group_id}).sort("created_at", -1).limit(limit).to_list(limit)
    messages.reverse()  # oldest first
    return [
        Message(
            id=str(m["_id"]), group_id=m["group_id"], user_id=m["user_id"], username=m["username"],
            avatar=m.get("avatar"), content=m["content"], created_at=m["created_at"],
        )
        for m in messages
    ]


@router.get("/activities", response_model=List[Activity])
async def get_activities(group_id: str, limit: int = Query(50, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    await get_member_group(group_id, current_user)
    activities = await db.activities.find({"group_id": group_id}).sort("created_at", -1).limit(limit).to_list(limit)
    return [
        Activity(
            id=str(a["_id"]), group_id=a["group_id"], user_id=a["user_id"], username=a["username"],
            activity_type=a["activity_type"], description=a["description"], created_at=a["created_at"],
        )
        for a in activities
    ]
