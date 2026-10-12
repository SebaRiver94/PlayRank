from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends

from core.db import db
from core.security import get_current_user
from models.group import GameType, GameTypeCreate, to_game_type
from services.permissions import get_member_group

router = APIRouter(prefix="/groups/{group_id}/game-types", tags=["game-types"])


@router.post("", response_model=GameType)
async def create_game_type(group_id: str, game_data: GameTypeCreate, current_user: dict = Depends(get_current_user)):
    await get_member_group(group_id, current_user)
    game = {
        "name": game_data.name,
        "icon": game_data.icon,
        "group_id": group_id,
        "created_at": datetime.utcnow(),
    }
    result = await db.game_types.insert_one(game)
    game["_id"] = result.inserted_id
    return to_game_type(game)


@router.get("", response_model=List[GameType])
async def get_game_types(group_id: str, current_user: dict = Depends(get_current_user)):
    await get_member_group(group_id, current_user)
    game_types = await db.game_types.find({"group_id": group_id}).limit(100).to_list(100)
    return [to_game_type(gt) for gt in game_types]
