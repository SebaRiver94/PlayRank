from typing import Optional

from bson import ObjectId
from fastapi import HTTPException


def parse_oid_or_none(value: str) -> Optional[ObjectId]:
    return ObjectId(value) if value and ObjectId.is_valid(value) else None


def parse_oid(value: str, resource: str = "Resource") -> ObjectId:
    """Parse an id coming from the client; invalid ids are treated as not found."""
    oid = parse_oid_or_none(value)
    if not oid:
        raise HTTPException(status_code=404, detail=f"{resource} not found")
    return oid


def serialize_doc(doc: dict) -> dict:
    """Convert a MongoDB document to a JSON-serializable dict without secrets."""
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    doc.pop("password", None)
    doc.pop("email_normalized", None)
    for key, value in doc.items():
        if hasattr(value, "isoformat"):
            doc[key] = value.isoformat()
    return doc
