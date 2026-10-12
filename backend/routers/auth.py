from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pymongo.errors import DuplicateKeyError

from core.db import db
from core.security import create_access_token, get_current_user, hash_password, verify_password
from models.user import Token, UserCreate, UserLogin, UserProfile, to_profile
from services.rate_limit import clear_login_failures, ensure_login_allowed, record_login_failure

router = APIRouter(prefix="/auth", tags=["auth"])


def normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    email_normalized = normalize_email(user_data.email)
    if await db.users.find_one({"email_normalized": email_normalized}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": user_data.username}):
        raise HTTPException(status_code=400, detail="Username already taken")

    user = {
        "email": email_normalized,
        "email_normalized": email_normalized,
        "username": user_data.username,
        "password": hash_password(user_data.password),
        "avatar": None,
        "bio": None,
        "favorite_games": [],
        "external_accounts": {},
        "created_at": datetime.utcnow(),
    }
    try:
        result = await db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    user["_id"] = result.inserted_id

    return Token(
        access_token=create_access_token(str(result.inserted_id)),
        token_type="bearer",
        user=to_profile(user, include_email=True),
    )


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, request: Request):
    email_normalized = normalize_email(user_data.email)
    await ensure_login_allowed(email_normalized, request)

    user = await db.users.find_one({"email_normalized": email_normalized})
    # verify_password runs against a dummy hash when the user doesn't exist (timing-safe)
    if not verify_password(user_data.password, user["password"] if user else None) or not user:
        await record_login_failure(email_normalized, request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    await clear_login_failures(email_normalized, request)
    return Token(
        access_token=create_access_token(str(user["_id"])),
        token_type="bearer",
        user=to_profile(user, include_email=True),
    )


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    return to_profile(current_user, include_email=True)
