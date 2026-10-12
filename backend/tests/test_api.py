"""End-to-end API tests for PlayRank (Etapa 1).

Run: cd /app/backend && python -m pytest tests -q
Uses the running backend (default http://localhost:8001). Every document created by the
tests is tagged with a unique run id and removed at the end; existing data is never touched.
"""
import os
import time
import uuid
from datetime import datetime

import pytest
import requests
import socketio
from bson import ObjectId
from pymongo import MongoClient

from core.config import MONGO_URL, DB_NAME

BASE = os.environ.get("PLAYRANK_TEST_URL", "http://localhost:8001")
API = f"{BASE}/api"
RUN = uuid.uuid4().hex[:8]
PASSWORD = "TestPass123!"


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def created(mongo):
    """Track created ids and clean them up afterwards."""
    ids = {"users": [], "groups": []}
    started = datetime.utcnow()
    yield ids
    mongo.login_attempts.delete_many({"created_at": {"$gte": started}})
    group_ids = [str(g) for g in ids["groups"]]
    mongo.groups.delete_many({"_id": {"$in": ids["groups"]}})
    for coll in ("matches", "stats", "activities", "messages", "game_types"):
        mongo[coll].delete_many({"group_id": {"$in": group_ids}})
    mongo.users.delete_many({"_id": {"$in": ids["users"]}})


def register(created, name):
    email = f"qa_{name}_{RUN}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PASSWORD, "username": f"qa_{name}_{RUN}"})
    assert r.status_code == 200, r.text
    body = r.json()
    created["users"].append(ObjectId(body["user"]["id"]))
    return {"token": body["access_token"], "id": body["user"]["id"], "email": email,
            "h": {"Authorization": f"Bearer {body['access_token']}"}}


@pytest.fixture(scope="module")
def users(created):
    return register(created, "alice"), register(created, "bob"), register(created, "eve")


@pytest.fixture(scope="module")
def group(users, created):
    alice, bob, _ = users
    r = requests.post(f"{API}/groups", json={"name": f"QA Group {RUN}", "description": "test"}, headers=alice["h"])
    assert r.status_code == 200, r.text
    g = r.json()
    created["groups"].append(ObjectId(g["id"]))
    assert requests.post(f"{API}/groups/{g['id']}/join", headers=bob["h"]).status_code == 200
    gt = requests.post(f"{API}/groups/{g['id']}/game-types", json={"name": "Chess"}, headers=alice["h"]).json()
    return {"id": g["id"], "game_type_id": gt["id"]}


# ---------- Auth ----------

def test_health():
    assert requests.get(f"{API}/health").json() == {"status": "ok"}


def test_register_validation():
    bad = [
        {"email": "x@example.com", "password": "short", "username": "valid_name"},
        {"email": "x@example.com", "password": PASSWORD, "username": "a"},
        {"email": "x@example.com", "password": PASSWORD, "username": "bad name!"},
        {"email": "not-an-email", "password": PASSWORD, "username": "valid_name"},
    ]
    for payload in bad:
        assert requests.post(f"{API}/auth/register", json=payload).status_code == 422


def test_duplicate_email_case_insensitive(users):
    alice = users[0]
    r = requests.post(f"{API}/auth/register", json={"email": alice["email"].upper(), "password": PASSWORD, "username": f"qa_dup_{RUN}"})
    assert r.status_code == 400


def test_login_and_me(users):
    alice = users[0]
    r = requests.post(f"{API}/auth/login", json={"email": alice["email"].upper(), "password": PASSWORD})
    assert r.status_code == 200
    me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["email"] == alice["email"] and "password" not in me


def test_invalid_tokens_are_401():
    assert requests.get(f"{API}/auth/me").status_code == 401
    assert requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer bad.token.here"}).status_code == 401


def test_login_rate_limit(created):
    email = f"qa_ratelimit_{RUN}@example.com"
    codes = [requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong-pass"}).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


# ---------- Privacy / validation ----------

def test_other_users_email_hidden(users, group):
    alice, bob, _ = users
    assert requests.get(f"{API}/users/{bob['id']}", headers=alice["h"]).json()["email"] is None
    members = requests.get(f"{API}/groups/{group['id']}/members", headers=alice["h"]).json()
    emails = {m["id"]: m["email"] for m in members}
    assert emails[alice["id"]] == alice["email"] and emails[bob["id"]] is None


def test_invalid_object_ids_return_404(users):
    h = users[0]["h"]
    assert requests.get(f"{API}/groups/abc", headers=h).status_code == 404
    assert requests.get(f"{API}/groups/abc/matches", headers=h).status_code == 404
    assert requests.get(f"{API}/users/abc", headers=h).status_code == 404


def test_non_member_forbidden(users, group):
    eve = users[2]
    assert requests.get(f"{API}/groups/{group['id']}", headers=eve["h"]).status_code == 403
    assert requests.get(f"{API}/groups/{group['id']}/leaderboard", headers=eve["h"]).status_code == 403


def test_profile_update_validation(users):
    h = users[0]["h"]
    assert requests.put(f"{API}/users/profile", json={"bio": "x" * 301}, headers=h).status_code == 422
    assert requests.put(f"{API}/users/profile", json={"external_accounts": {"myspace": "x"}}, headers=h).status_code == 422
    r = requests.put(f"{API}/users/profile", json={"bio": "Hola", "external_accounts": {"steam": "https://steamcommunity.com/id/qa"}}, headers=h)
    assert r.status_code == 200 and r.json()["bio"] == "Hola"


# ---------- Matches & leaderboard ----------

def test_match_validation(users, group):
    alice, bob, eve = users
    base = {"group_id": group["id"], "game_type_id": group["game_type_id"], "date": datetime.utcnow().isoformat()}
    cases = [
        ({"players": [alice["id"]], "winner_ids": [alice["id"]]}, 422),            # single player
        ({"players": [alice["id"], bob["id"]], "winner_ids": [eve["id"]]}, 422),   # winner not a player
        ({"players": [alice["id"], eve["id"]], "winner_ids": [alice["id"]]}, 400),  # non-member player
    ]
    for extra, code in cases:
        assert requests.post(f"{API}/matches", json={**base, **extra}, headers=alice["h"]).status_code == code
    wrong_game = {**base, "game_type_id": str(ObjectId()), "players": [alice["id"], bob["id"]], "winner_ids": [alice["id"]]}
    assert requests.post(f"{API}/matches", json=wrong_game, headers=alice["h"]).status_code == 400


def test_match_updates_leaderboard(users, group):
    alice, bob, _ = users
    payload = {"group_id": group["id"], "game_type_id": group["game_type_id"], "date": datetime.utcnow().isoformat(),
               "players": [alice["id"], bob["id"]], "winner_ids": [alice["id"]], "score": "1-0"}
    for _ in range(2):
        assert requests.post(f"{API}/matches", json=payload, headers=alice["h"]).status_code == 200
    board = requests.get(f"{API}/groups/{group['id']}/leaderboard", headers=bob["h"]).json()
    top = board[0]
    assert top["user_id"] == alice["id"] and top["wins"] == 2 and top["current_streak"] == 2 and top["win_rate"] == 100
    stats = requests.get(f"{API}/groups/{group['id']}/stats/{bob['id']}", headers=bob["h"]).json()
    assert stats["losses"] == 2 and stats["streak_type"] == "loss"
    assert len(requests.get(f"{API}/groups/{group['id']}/matches", headers=bob["h"]).json()) == 2


# ---------- Socket.IO ----------

def _socket(token=None):
    sio = socketio.Client(reconnection=False)
    sio.connect(BASE, socketio_path="api/socket.io", transports=["polling"], auth={"token": token} if token else None)
    return sio


def test_socket_rejects_without_valid_token():
    for token in (None, "bad-token"):
        with pytest.raises(socketio.exceptions.ConnectionError):
            _socket(token)


def test_socket_chat_flow(users, group):
    alice, bob, eve = users
    received = []
    sb = _socket(bob["token"])
    sb.on("new_message", lambda data: received.append(data))
    assert sb.call("join_group", {"group_id": group["id"]})["ok"] is True

    sa = _socket(alice["token"])
    assert sa.call("join_group", {"group_id": group["id"]})["ok"] is True
    # user_id in payload is ignored: the author comes from the token
    ack = sa.call("send_message", {"group_id": group["id"], "content": "hola", "user_id": bob["id"]})
    assert ack["ok"] is True and ack["message"]["user_id"] == alice["id"]

    se = _socket(eve["token"])
    assert se.call("join_group", {"group_id": group["id"]})["ok"] is False
    assert se.call("send_message", {"group_id": group["id"], "content": "spam"})["ok"] is False

    deadline = time.time() + 5
    while not received and time.time() < deadline:
        time.sleep(0.1)
    for s in (sa, sb, se):
        s.disconnect()

    assert received and received[0]["content"] == "hola"
    history = requests.get(f"{API}/groups/{group['id']}/messages", headers=bob["h"]).json()
    assert [m["content"] for m in history] == ["hola"]
