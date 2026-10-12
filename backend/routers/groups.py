from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from core.db import db
from core.security import get_current_user
from models.group import Group, GroupCreate, GroupUpdate, to_group
from models.user import UserProfile, to_profile
from services.activity import create_activity
from services.permissions import get_group_or_404, get_member_group

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("", response_model=Group)
async def create_group(group_data: GroupCreate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    group = {
        "name": group_data.name,
        "icon": group_data.icon,
        "description": group_data.description,
        "owner_id": user_id,
        "members": [user_id],
        "created_at": datetime.utcnow(),
    }
    result = await db.groups.insert_one(group)
    group["_id"] = result.inserted_id

    await create_activity(
        str(result.inserted_id), user_id, current_user["username"],
        "group_created", f"{current_user['username']} created the group",
    )
    return to_group(group)


@router.get("", response_model=List[Group])
async def get_user_groups(current_user: dict = Depends(get_current_user)):
    groups = await db.groups.find({"members": str(current_user["_id"])}).limit(100).to_list(100)
    return [to_group(g) for g in groups]


@router.get("/{group_id}", response_model=Group)
async def get_group(group_id: str, current_user: dict = Depends(get_current_user)):
    return to_group(await get_member_group(group_id, current_user))


@router.put("/{group_id}", response_model=Group)
async def update_group(group_id: str, group_update: GroupUpdate, current_user: dict = Depends(get_current_user)):
    group = await get_group_or_404(group_id)
    if group["owner_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Only group owner can update")

    update_data = group_update.model_dump(exclude_none=True)
    if update_data:
        await db.groups.update_one({"_id": group["_id"]}, {"$set": update_data})
    return to_group(await db.groups.find_one({"_id": group["_id"]}))


@router.post("/{group_id}/join")
async def join_group(group_id: str, current_user: dict = Depends(get_current_user)):
    group = await get_group_or_404(group_id)
    user_id = str(current_user["_id"])
    if user_id in group["members"]:
        raise HTTPException(status_code=400, detail="Already a member")

    await db.groups.update_one({"_id": group["_id"]}, {"$addToSet": {"members": user_id}})
    await create_activity(
        group_id, user_id, current_user["username"],
        "member_joined", f"{current_user['username']} joined the group 👋",
    )
    return {"message": "Joined group successfully"}


@router.get("/{group_id}/members", response_model=List[UserProfile])
async def get_group_members(group_id: str, current_user: dict = Depends(get_current_user)):
    group = await get_member_group(group_id, current_user)
    member_ids = [ObjectId(mid) for mid in group["members"] if ObjectId.is_valid(mid)]
    users = await db.users.find({"_id": {"$in": member_ids}}).to_list(len(member_ids))
    # Emails of other members are private
    return [to_profile(u, include_email=u["_id"] == current_user["_id"]) for u in users]
