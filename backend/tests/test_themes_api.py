"""API tests for the visual theme preference.

Run: cd backend && python -m pytest tests/test_themes_api.py -q
Requires a running backend (default http://localhost:8001, override with PLAYRANK_TEST_URL)
and the same environment as tests/test_api.py (MONGO_URL, DB_NAME, SECRET_KEY). Use a
dedicated test database: every document created here is tagged with a unique run id and
removed at the end, and existing data is never touched.
"""
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
import requests
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
    ids = {"users": [], "groups": []}
    started = datetime.utcnow()
    yield ids
    mongo.login_attempts.delete_many({"created_at": {"$gte": started}})
    group_ids = [str(g) for g in ids["groups"]]
    mongo.groups.delete_many({"_id": {"$in": ids["groups"]}})
    mongo.activities.delete_many({"group_id": {"$in": group_ids}})
    mongo.users.delete_many({"_id": {"$in": ids["users"]}})


def register_raw(name, theme=None):
    payload = {
        "email": f"qa_th_{name}_{RUN}@example.com",
        "password": PASSWORD,
        "username": f"qa_th_{name}_{RUN}",
    }
    if theme is not None:
        payload["theme"] = theme
    return requests.post(f"{API}/auth/register", json=payload), payload


def new_user(created, name, theme=None):
    r, payload = register_raw(name, theme)
    assert r.status_code == 200, r.text
    body = r.json()
    created["users"].append(ObjectId(body["user"]["id"]))
    return {
        "id": body["user"]["id"], "email": payload["email"], "register": body["user"],
        "h": {"Authorization": f"Bearer {body['access_token']}"},
    }


def put_profile(user, **body):
    return requests.put(f"{API}/users/profile", json=body, headers=user["h"])


def me(user):
    r = requests.get(f"{API}/auth/me", headers=user["h"])
    assert r.status_code == 200, r.text
    return r.json()


# ---------- registration ----------

def test_register_without_theme_defaults_to_neo(created):
    u = new_user(created, "def")
    assert u["register"]["theme"] == "neo"
    assert u["register"]["theme_version"] == 0


@pytest.mark.parametrize("theme", ["neo", "sakura", "core"])
def test_register_with_each_theme(created, theme):
    u = new_user(created, f"r{theme}", theme)
    assert u["register"]["theme"] == theme
    assert me(u)["theme"] == theme


@pytest.mark.parametrize("idx,theme", list(enumerate(["dark", "Sakura", "", "neo2", 5])))
def test_register_with_invalid_theme_is_422_and_creates_nothing(idx, theme, mongo):
    r, payload = register_raw(f"bad{idx}", theme)
    assert r.status_code == 422
    assert mongo.users.find_one({"email_normalized": payload["email"]}) is None


def test_login_returns_the_saved_theme(created):
    u = new_user(created, "login", "sakura")
    r = requests.post(f"{API}/auth/login", json={"email": u["email"], "password": PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["theme"] == "sakura"


# ---------- updating through PUT /users/profile ----------

def test_put_theme_persists_and_bumps_version(created):
    u = new_user(created, "put")
    r = put_profile(u, theme="sakura")
    assert r.status_code == 200, r.text
    assert (r.json()["theme"], r.json()["theme_version"]) == ("sakura", 1)
    assert (me(u)["theme"], me(u)["theme_version"]) == ("sakura", 1)
    login = requests.post(f"{API}/auth/login", json={"email": u["email"], "password": PASSWORD})
    assert login.json()["user"]["theme"] == "sakura"


def test_updating_other_fields_does_not_change_theme_or_version(created):
    u = new_user(created, "bio", "core")
    r = put_profile(u, bio="Hola")
    assert r.status_code == 200, r.text
    assert (r.json()["bio"], r.json()["theme"], r.json()["theme_version"]) == ("Hola", "core", 0)


def test_put_theme_does_not_clobber_other_profile_fields(created):
    u = new_user(created, "keep")
    assert put_profile(u, bio="Hola", external_accounts={"steam": "https://steamcommunity.com/id/qa"}).status_code == 200
    r = put_profile(u, theme="core")
    assert r.status_code == 200, r.text
    assert r.json()["bio"] == "Hola"
    assert r.json()["external_accounts"] == {"steam": "https://steamcommunity.com/id/qa"}


def test_put_invalid_theme_is_422_and_changes_nothing(created):
    u = new_user(created, "inv", "core")
    assert put_profile(u, theme="dark").status_code == 422
    assert put_profile(u, theme="core", theme_base_version=-1).status_code == 422
    assert put_profile(u, theme_base_version=0, bio="x").status_code == 422
    assert me(u)["theme"] == "core" and me(u)["bio"] is None


def test_put_theme_requires_authentication():
    assert requests.put(f"{API}/users/profile", json={"theme": "core"}).status_code == 401
    assert requests.put(f"{API}/users/profile", json={"theme": "core"},
                        headers={"Authorization": "Bearer nope"}).status_code == 401


def test_existing_username_rules_still_apply(created):
    a = new_user(created, "una")
    b = new_user(created, "unb")
    r = put_profile(b, username=f"qa_th_una_{RUN}")
    assert r.status_code == 400
    assert a["id"] != b["id"]


# ---------- multi-device safety ----------

def test_stale_device_gets_409_with_current_value_and_nothing_is_written(created):
    u = new_user(created, "conf")
    # Both "devices" last saw version 0.
    assert put_profile(u, theme="sakura", theme_base_version=0).status_code == 200  # device 1
    r = put_profile(u, theme="core", theme_base_version=0, bio="no deberia guardarse")  # device 2
    assert r.status_code == 409, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "theme_conflict"
    assert (detail["theme"], detail["theme_version"]) == ("sakura", 1)
    state = me(u)
    assert (state["theme"], state["theme_version"], state["bio"]) == ("sakura", 1, None)  # atomic: bio untouched
    # Device 2 adopts the server state and retries deliberately.
    assert put_profile(u, theme="core", theme_base_version=1).status_code == 200
    assert (me(u)["theme"], me(u)["theme_version"]) == ("core", 2)


def test_without_base_version_it_is_last_write_wins(created):
    u = new_user(created, "lww")
    assert put_profile(u, theme="sakura").status_code == 200
    assert put_profile(u, theme="core").status_code == 200
    assert (me(u)["theme"], me(u)["theme_version"]) == ("core", 2)


def test_resending_the_current_theme_is_idempotent_even_with_stale_base(created):
    u = new_user(created, "idem")
    assert put_profile(u, theme="sakura", theme_base_version=0).status_code == 200
    r = put_profile(u, theme="sakura", theme_base_version=0)
    assert r.status_code == 200, r.text
    assert (r.json()["theme"], r.json()["theme_version"]) == ("sakura", 1)  # no spurious bump


def test_concurrent_writes_with_same_base_only_one_wins(created):
    u = new_user(created, "race")
    barrier = threading.Barrier(2)

    def attempt(theme):
        barrier.wait()
        return put_profile(u, theme=theme, theme_base_version=0).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(pool.map(attempt, ["sakura", "core"]))
    assert codes == [200, 409]
    assert me(u)["theme_version"] == 1


def test_legacy_user_without_theme_fields(created, mongo):
    u = new_user(created, "legacy")
    mongo.users.update_one({"_id": ObjectId(u["id"])}, {"$unset": {"theme": "", "theme_version": "", "theme_updated_at": ""}})
    state = me(u)
    assert (state["theme"], state["theme_version"]) == ("neo", 0)
    r = put_profile(u, theme="sakura", theme_base_version=0)
    assert r.status_code == 200, r.text
    assert (r.json()["theme"], r.json()["theme_version"]) == ("sakura", 1)


# ---------- privacy ----------

def test_theme_is_private_in_public_profiles_and_group_members(created):
    alice = new_user(created, "pa", "sakura")
    bob = new_user(created, "pb", "core")

    # Another user's profile: theme and version are hidden (null).
    other = requests.get(f"{API}/users/{alice['id']}", headers=bob["h"])
    assert other.status_code == 200
    assert other.json()["theme"] is None and other.json()["theme_version"] is None
    # Own profile through the same endpoint: visible.
    own = requests.get(f"{API}/users/{bob['id']}", headers=bob["h"])
    assert (own.json()["theme"], own.json()["theme_version"]) == ("core", 0)

    # Group members: only the caller's own entry carries the preference.
    g = requests.post(f"{API}/groups", json={"name": f"QA Theme {RUN}"}, headers=alice["h"])
    assert g.status_code == 200, g.text
    group_id = g.json()["id"]
    created["groups"].append(ObjectId(group_id))
    assert requests.post(f"{API}/groups/{group_id}/join", headers=bob["h"]).status_code == 200
    members = requests.get(f"{API}/groups/{group_id}/members", headers=bob["h"]).json()
    by_id = {m["id"]: m for m in members}
    assert by_id[bob["id"]]["theme"] == "core"
    assert by_id[alice["id"]]["theme"] is None and by_id[alice["id"]]["theme_version"] is None
    assert by_id[alice["id"]]["email"] is None  # existing privacy rule unchanged
