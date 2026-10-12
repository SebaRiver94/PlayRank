"""Idempotent, additive-only startup migrations. Never deletes or renames existing data."""
import logging

from pymongo import ASCENDING, DESCENDING

from core.config import LOGIN_WINDOW_SECONDS
from core.db import db

logger = logging.getLogger(__name__)


async def backfill_email_normalized():
    cursor = db.users.find({"email_normalized": {"$exists": False}}, {"email": 1})
    async for user in cursor:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"email_normalized": user["email"].strip().lower()}},
        )


async def create_indexes():
    await db.users.create_index("email_normalized", unique=True, name="uq_users_email_normalized")
    await db.users.create_index("username", unique=True, name="uq_users_username")
    await db.groups.create_index("members", name="ix_groups_members")
    await db.game_types.create_index("group_id", name="ix_game_types_group")
    await db.matches.create_index([("group_id", ASCENDING), ("date", DESCENDING)], name="ix_matches_group_date")
    await db.stats.create_index([("user_id", ASCENDING), ("group_id", ASCENDING)], unique=True, name="uq_stats_user_group")
    await db.stats.create_index([("group_id", ASCENDING), ("wins", DESCENDING)], name="ix_stats_group_wins")
    await db.messages.create_index([("group_id", ASCENDING), ("created_at", DESCENDING)], name="ix_messages_group_date")
    await db.activities.create_index([("group_id", ASCENDING), ("created_at", DESCENDING)], name="ix_activities_group_date")
    await db.login_attempts.create_index("created_at", expireAfterSeconds=LOGIN_WINDOW_SECONDS, name="ttl_login_attempts")
    await db.login_attempts.create_index("key", name="ix_login_attempts_key")


async def run_startup_migrations():
    await backfill_email_normalized()
    try:
        await create_indexes()
    except Exception as exc:  # duplicates in legacy data must not take the API down
        logger.error("Index creation failed: %s", exc)
