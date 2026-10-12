from datetime import datetime
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from core.db import db
from core.security import get_current_user
from core.utils import parse_oid_or_none
from models.match import Match, MatchCreate, to_match
from services.activity import create_activity
from services.permissions import get_member_group
from services.stats import update_user_stats

router = APIRouter(tags=["matches"])


@router.post("/matches", response_model=Match)
async def create_match(match_data: MatchCreate, current_user: dict = Depends(get_current_user)):
    group = await get_member_group(match_data.group_id, current_user)

    non_members = set(match_data.players) - set(group["members"])
    if non_members:
        raise HTTPException(status_code=400, detail="All players must be members of the group")

    game_oid = parse_oid_or_none(match_data.game_type_id)
    game_type = await db.game_types.find_one({"_id": game_oid, "group_id": match_data.group_id}) if game_oid else None
    if not game_type:
        raise HTTPException(status_code=400, detail="Game type not found in this group")

    match = {
        "game_type_id": match_data.game_type_id,
        "group_id": match_data.group_id,
        "date": match_data.date,
        "players": match_data.players,
        "winner_ids": match_data.winner_ids,
        "score": match_data.score,
        "notes": match_data.notes,
        "created_by": str(current_user["_id"]),
        "created_at": datetime.utcnow(),
    }
    result = await db.matches.insert_one(match)
    match["_id"] = result.inserted_id

    for player_id in match_data.players:
        await update_user_stats(player_id, match_data.group_id, player_id in match_data.winner_ids)

    winners = await db.users.find(
        {"_id": {"$in": [ObjectId(w) for w in match_data.winner_ids]}}
    ).to_list(len(match_data.winner_ids))
    winners_str = ", ".join(u["username"] for u in winners)
    await create_activity(
        match_data.group_id, str(current_user["_id"]), current_user["username"],
        "match_added", f"New {game_type['name']} match: {winners_str} won! 🎮",
    )
    return to_match(match)


@router.get("/groups/{group_id}/matches", response_model=List[Match])
async def get_group_matches(group_id: str, current_user: dict = Depends(get_current_user)):
    await get_member_group(group_id, current_user)
    matches = await db.matches.find({"group_id": group_id}).sort("date", -1).limit(50).to_list(50)
    return [to_match(m) for m in matches]
