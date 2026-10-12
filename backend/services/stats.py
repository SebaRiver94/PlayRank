from core.db import db


async def update_user_stats(user_id: str, group_id: str, is_winner: bool):
    """Update a player's statistics in a group after a match."""
    stats = await db.stats.find_one({"user_id": user_id, "group_id": group_id}) or {
        "user_id": user_id,
        "group_id": group_id,
        "total_matches": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "current_streak": 0,
        "streak_type": "none",
        "best_win_streak": 0,
    }
    stats.pop("_id", None)
    stats["total_matches"] += 1

    result = "win" if is_winner else "loss"
    stats["wins" if is_winner else "losses"] += 1
    if stats["streak_type"] == result:
        stats["current_streak"] += 1
    else:
        stats["current_streak"] = 1
        stats["streak_type"] = result
    if is_winner:
        stats["best_win_streak"] = max(stats["best_win_streak"], stats["current_streak"])

    stats["win_rate"] = stats["wins"] / stats["total_matches"] * 100

    await db.stats.update_one(
        {"user_id": user_id, "group_id": group_id},
        {"$set": stats},
        upsert=True,
    )
