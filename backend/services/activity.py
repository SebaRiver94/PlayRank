from datetime import datetime

from core.db import db
from core.utils import serialize_doc
from realtime.socket import sio


async def create_activity(group_id: str, user_id: str, username: str, activity_type: str, description: str):
    activity = {
        "group_id": group_id,
        "user_id": user_id,
        "username": username,
        "activity_type": activity_type,
        "description": description,
        "created_at": datetime.utcnow(),
    }
    result = await db.activities.insert_one(activity)
    activity["_id"] = result.inserted_id
    await sio.emit("activity", serialize_doc(activity), room=group_id)
    return result.inserted_id
