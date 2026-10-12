from fastapi import HTTPException

from core.db import db
from core.utils import parse_oid


async def get_group_or_404(group_id: str) -> dict:
    group = await db.groups.find_one({"_id": parse_oid(group_id, "Group")})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


async def get_member_group(group_id: str, user: dict) -> dict:
    """Return the group if the user is a member, otherwise 404/403."""
    group = await get_group_or_404(group_id)
    if str(user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return group
