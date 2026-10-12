"""Visual theme preference: constants and pure helpers.

Everything here is pure Python (no I/O, no third-party imports) so it can be unit-tested
without a database or a running server.

Data model (additive, stored on the `users` document):
    theme            "neo" | "sakura" | "core"   (missing/invalid -> "neo" when read)
    theme_version    int, incremented on every real theme change (missing -> 0)
    theme_updated_at datetime (UTC), informational

Multi-device safety: a client may send the `theme_version` it last saw as
`theme_base_version`. The write then only applies if the stored version still matches
(compare-and-set done atomically by MongoDB in a single update_one filter); otherwise the
API answers 409 and the client refreshes instead of silently overwriting a newer choice
made on another device. Without `theme_base_version` the write is last-write-wins, which
keeps older clients working.
"""
from datetime import datetime
from typing import Optional, Tuple

THEME_IDS = ("neo", "sakura", "core")
DEFAULT_THEME = "neo"


def normalize_theme(value) -> str:
    """Return a valid theme id; anything missing/unknown falls back to the default."""
    return value if isinstance(value, str) and value in THEME_IDS else DEFAULT_THEME


def theme_version_of(user: dict) -> int:
    """Stored theme version, treating a missing or corrupt value as 0 (legacy users)."""
    value = user.get("theme_version", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def version_filter(base_version: int) -> dict:
    """Extra Mongo query that only matches while the stored version equals `base_version`.

    Legacy users have no `theme_version` field, which is equivalent to version 0.
    """
    if base_version == 0:
        return {"$or": [{"theme_version": 0}, {"theme_version": {"$exists": False}}]}
    return {"theme_version": base_version}


def build_profile_write(
    current_user: dict,
    fields: dict,
    theme: Optional[str],
    base_version: Optional[int],
    now: datetime,
) -> Optional[Tuple[dict, dict]]:
    """Build the Mongo write for PUT /users/profile.

    `fields` are the already-validated non-theme profile fields (it is not mutated).
    Returns None when there is nothing to write, otherwise `(extra_query, update)` where
    `extra_query` is merged into the `_id` filter (empty unless a compare-and-set on the
    theme version is requested) and `update` is the Mongo update document.

    Re-sending the theme the account already has is a no-op for the theme: it neither
    bumps the version nor conflicts, so a stale client that merely re-affirms the current
    value is harmless.
    """
    set_doc = dict(fields)
    update: dict = {}
    extra_query: dict = {}

    if theme is not None and current_user.get("theme") != theme:
        set_doc["theme"] = theme
        set_doc["theme_updated_at"] = now
        update["$inc"] = {"theme_version": 1}
        if base_version is not None:
            extra_query = version_filter(base_version)

    if set_doc:
        update["$set"] = set_doc
    if not update:
        return None
    return extra_query, update
