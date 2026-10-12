"""Socket.IO server (served at /api/socket.io). Every connection must send a JWT."""
import logging
from datetime import datetime

import socketio
from socketio.exceptions import ConnectionRefusedError

from core.config import is_origin_allowed
from core.db import db
from core.security import get_user_from_token
from core.utils import parse_oid_or_none, serialize_doc
from models.social import MAX_MESSAGE_LENGTH

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=is_origin_allowed,
    logger=False,
    engineio_logger=False,
)


async def _member_group(sid, group_id):
    """Return (session, group) if the connected user belongs to the group."""
    session = await sio.get_session(sid)
    group_oid = parse_oid_or_none(group_id or "")
    if not group_oid:
        return session, None
    group = await db.groups.find_one({"_id": group_oid, "members": session["user_id"]})
    return session, group


@sio.event
async def connect(sid, environ, auth):
    token = (auth or {}).get("token", "") if isinstance(auth, dict) else ""
    user = await get_user_from_token(token)
    if not user:
        raise ConnectionRefusedError("authentication failed")
    await sio.save_session(sid, {"user_id": str(user["_id"])})


@sio.event
async def disconnect(sid):
    pass


@sio.event
async def join_group(sid, data):
    group_id = (data or {}).get("group_id")
    _, group = await _member_group(sid, group_id)
    if not group:
        return {"ok": False, "error": "Not a member of this group"}
    await sio.enter_room(sid, group_id)
    return {"ok": True}


@sio.event
async def leave_group(sid, data):
    group_id = (data or {}).get("group_id")
    if group_id:
        await sio.leave_room(sid, group_id)
    return {"ok": True}


@sio.event
async def send_message(sid, data):
    data = data or {}
    group_id = data.get("group_id")
    content = (data.get("content") or "").strip()
    if not content or len(content) > MAX_MESSAGE_LENGTH:
        return {"ok": False, "error": "Invalid message"}

    session, group = await _member_group(sid, group_id)
    if not group:
        return {"ok": False, "error": "Not a member of this group"}

    # The author always comes from the authenticated session, never from the client payload.
    user = await db.users.find_one({"_id": parse_oid_or_none(session["user_id"])})
    if not user:
        return {"ok": False, "error": "User not found"}

    message = {
        "group_id": group_id,
        "user_id": session["user_id"],
        "username": user["username"],
        "avatar": user.get("avatar"),
        "content": content,
        "created_at": datetime.utcnow(),
    }
    result = await db.messages.insert_one(message)
    message["_id"] = result.inserted_id
    payload = serialize_doc(message)
    await sio.emit("new_message", payload, room=group_id)
    return {"ok": True, "message": payload}
