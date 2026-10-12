"""Unit tests for the theme preference (no running server and no MongoDB required).

Run: cd backend && python -m pytest tests/test_themes_unit.py -q
"""
from datetime import datetime, timezone, timedelta
from typing import get_args

import pytest
from pydantic import ValidationError

from core.themes import (
    DEFAULT_THEME, THEME_IDS, build_profile_write, normalize_theme, theme_version_of, version_filter,
)
from models.user import ThemeId, UserCreate, UserUpdate, to_profile

NOW = datetime(2026, 10, 12, tzinfo=timezone.utc)
CREATED = NOW - timedelta(days=1)


def make_user(**extra):
    base = {"_id": "u1", "email": "a@example.com", "username": "alice", "created_at": CREATED}
    base.update(extra)
    return base


# ---------- constants / normalization ----------

def test_neo_is_default_and_ids_are_the_three_themes():
    assert DEFAULT_THEME == "neo"
    assert THEME_IDS == ("neo", "sakura", "core")


def test_pydantic_literal_matches_theme_ids():
    assert tuple(get_args(ThemeId)) == THEME_IDS


@pytest.mark.parametrize("value", [None, "", "dark", "Neo", "SAKURA", 3, ["neo"], {}])
def test_normalize_theme_falls_back_to_default(value):
    assert normalize_theme(value) == "neo"


@pytest.mark.parametrize("theme", THEME_IDS)
def test_normalize_theme_keeps_valid_ids(theme):
    assert normalize_theme(theme) == theme


@pytest.mark.parametrize("raw,expected", [
    (None, 0), (-1, 0), ("3", 0), (True, 0), (2.5, 0), (0, 0), (7, 7),
])
def test_theme_version_of_is_defensive(raw, expected):
    assert theme_version_of({"theme_version": raw}) == expected


def test_theme_version_of_missing_field_is_zero():
    assert theme_version_of({}) == 0


# ---------- request models ----------

def test_register_theme_is_optional_and_old_payloads_still_valid():
    user = UserCreate(email="a@example.com", password="12345678", username="alice")
    assert user.theme is None


@pytest.mark.parametrize("theme", THEME_IDS)
def test_register_accepts_each_theme(theme):
    assert UserCreate(email="a@example.com", password="12345678", username="alice", theme=theme).theme == theme


@pytest.mark.parametrize("theme", ["", "dark", "Sakura", "NEO", "neo2", 1])
def test_register_rejects_unknown_theme(theme):
    with pytest.raises(ValidationError):
        UserCreate(email="a@example.com", password="12345678", username="alice", theme=theme)


def test_unknown_extra_fields_are_still_ignored():
    # Same behaviour as before this change: older/newer clients sending extra keys keep working.
    UserCreate(email="a@example.com", password="12345678", username="alice", something_else=1)
    UserUpdate(something_else=1)


def test_update_dump_excludes_unset_theme():
    assert UserUpdate(bio="hola").model_dump(exclude_none=True) == {"bio": "hola"}


def test_update_accepts_theme_with_and_without_base_version():
    assert UserUpdate(theme="core").model_dump(exclude_none=True) == {"theme": "core"}
    assert UserUpdate(theme="core", theme_base_version=0).model_dump(exclude_none=True) == {
        "theme": "core", "theme_base_version": 0,
    }


@pytest.mark.parametrize("kwargs", [
    {"theme": "dark"},
    {"theme": "core", "theme_base_version": -1},
    {"theme": "core", "theme_base_version": "x"},
    {"theme_base_version": 0},  # base version without a theme is meaningless
    {"theme_base_version": 3, "bio": "x"},
])
def test_update_rejects_invalid_theme_payloads(kwargs):
    with pytest.raises(ValidationError):
        UserUpdate(**kwargs)


# ---------- privacy of the preference ----------

def test_owner_profile_includes_theme_and_version():
    profile = to_profile(make_user(theme="sakura", theme_version=4), include_email=True)
    assert (profile.theme, profile.theme_version) == ("sakura", 4)
    assert profile.email == "a@example.com"


def test_other_users_never_see_theme_nor_email():
    profile = to_profile(make_user(theme="sakura", theme_version=4), include_email=False)
    assert profile.theme is None and profile.theme_version is None and profile.email is None
    dumped = profile.model_dump()
    assert dumped["theme"] is None and dumped["theme_version"] is None


def test_legacy_user_without_theme_reads_as_neo_version_zero():
    profile = to_profile(make_user(), include_email=True)
    assert (profile.theme, profile.theme_version) == ("neo", 0)


def test_corrupt_stored_values_are_sanitized():
    profile = to_profile(make_user(theme="hacked", theme_version=-5), include_email=True)
    assert (profile.theme, profile.theme_version) == ("neo", 0)


# ---------- write construction (compare-and-set) ----------

def test_nothing_to_write_returns_none():
    assert build_profile_write(make_user(), {}, None, None, NOW) is None


def test_non_theme_fields_only_do_not_touch_theme_or_version():
    fields = {"bio": "hola"}
    extra, update = build_profile_write(make_user(theme="core", theme_version=2), fields, None, None, NOW)
    assert extra == {}
    assert update == {"$set": {"bio": "hola"}}
    assert fields == {"bio": "hola"}  # input not mutated


def test_theme_change_without_base_is_last_write_wins_and_bumps_version():
    extra, update = build_profile_write(make_user(theme="neo", theme_version=1), {}, "sakura", None, NOW)
    assert extra == {}
    assert update["$set"] == {"theme": "sakura", "theme_updated_at": NOW}
    assert update["$inc"] == {"theme_version": 1}


def test_theme_change_with_base_adds_version_condition():
    extra, update = build_profile_write(make_user(theme="neo", theme_version=3), {}, "core", 3, NOW)
    assert extra == {"theme_version": 3}
    assert update["$inc"] == {"theme_version": 1}


def test_base_zero_also_matches_legacy_users_without_the_field():
    extra, _ = build_profile_write(make_user(), {}, "core", 0, NOW)
    assert extra == {"$or": [{"theme_version": 0}, {"theme_version": {"$exists": False}}]}
    assert version_filter(0) == extra
    assert version_filter(5) == {"theme_version": 5}


def test_same_theme_is_a_noop_even_with_stale_base():
    user = make_user(theme="sakura", theme_version=4)
    assert build_profile_write(user, {}, "sakura", 1, NOW) is None
    extra, update = build_profile_write(user, {"bio": "x"}, "sakura", 1, NOW)
    assert extra == {} and update == {"$set": {"bio": "x"}}  # no conflict, no bump


def test_theme_and_other_fields_travel_in_one_atomic_update():
    extra, update = build_profile_write(
        make_user(theme="neo", theme_version=0), {"bio": "x"}, "core", 0, NOW)
    assert update["$set"] == {"bio": "x", "theme": "core", "theme_updated_at": NOW}
    assert update["$inc"] == {"theme_version": 1}
    assert "$or" in extra


def test_legacy_user_choosing_neo_materializes_the_field():
    extra, update = build_profile_write(make_user(), {}, "neo", None, NOW)
    assert update["$set"]["theme"] == "neo" and update["$inc"] == {"theme_version": 1}
