from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
import os
import logging
from pathlib import Path
import socketio
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    # Generate a random secret key for development
    import secrets
    SECRET_KEY = secrets.token_urlsafe(32)
    logger.warning("SECRET_KEY not set - using generated key for development only!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200  # 30 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Socket.IO setup
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Create the main app
app = FastAPI()

# Create Socket.IO ASGI app
socket_app = socketio.ASGIApp(sio, app)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ===== PYDANTIC MODELS =====

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    username: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
    favorite_games: List[str] = []
    external_accounts: Dict[str, str] = {}
    created_at: datetime

class UserUpdate(BaseModel):
    username: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    favorite_games: Optional[List[str]] = None
    external_accounts: Optional[Dict[str, str]] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserProfile

class GroupCreate(BaseModel):
    name: str
    icon: Optional[str] = None
    description: Optional[str] = None

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None

class Group(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    description: Optional[str] = None
    owner_id: str
    members: List[str] = []
    created_at: datetime

class GameTypeCreate(BaseModel):
    name: str
    icon: Optional[str] = None

class GameType(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    group_id: str
    created_at: datetime

class MatchCreate(BaseModel):
    game_type_id: str
    group_id: str
    date: datetime
    players: List[str]
    winner_ids: List[str]
    score: Optional[str] = None
    notes: Optional[str] = None

class Match(BaseModel):
    id: str
    game_type_id: str
    group_id: str
    date: datetime
    players: List[str]
    winner_ids: List[str]
    score: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: datetime

class MessageCreate(BaseModel):
    group_id: str
    content: str

class Message(BaseModel):
    id: str
    group_id: str
    user_id: str
    username: str
    avatar: Optional[str] = None
    content: str
    created_at: datetime

class Activity(BaseModel):
    id: str
    group_id: str
    user_id: str
    username: str
    activity_type: str
    description: str
    created_at: datetime

class LeaderboardEntry(BaseModel):
    user_id: str
    username: str
    avatar: Optional[str] = None
    total_matches: int
    wins: int
    losses: int
    win_rate: float
    current_streak: int
    streak_type: str  # "win" or "loss"

class UserStats(BaseModel):
    user_id: str
    group_id: str
    total_matches: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    current_streak: int = 0
    streak_type: str = "none"
    best_win_streak: int = 0

# ===== HELPER FUNCTIONS =====

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise credentials_exception
        
        return user
    except JWTError:
        raise credentials_exception

def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    if "password" in doc:
        del doc["password"]
    return doc

async def create_activity(group_id: str, user_id: str, username: str, activity_type: str, description: str):
    """Create an activity entry"""
    activity = {
        "group_id": group_id,
        "user_id": user_id,
        "username": username,
        "activity_type": activity_type,
        "description": description,
        "created_at": datetime.utcnow()
    }
    result = await db.activities.insert_one(activity)
    
    # Emit Socket.IO event for real-time activity
    await sio.emit('activity', serialize_doc(activity), room=group_id)
    
    return result.inserted_id

async def update_user_stats(user_id: str, group_id: str, is_winner: bool):
    """Update user statistics after a match"""
    stats = await db.stats.find_one({"user_id": user_id, "group_id": group_id})
    
    if not stats:
        stats = {
            "user_id": user_id,
            "group_id": group_id,
            "total_matches": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "current_streak": 0,
            "streak_type": "none",
            "best_win_streak": 0
        }
    
    stats["total_matches"] += 1
    
    if is_winner:
        stats["wins"] += 1
        if stats["streak_type"] == "win":
            stats["current_streak"] += 1
        else:
            stats["current_streak"] = 1
            stats["streak_type"] = "win"
        
        if stats["current_streak"] > stats["best_win_streak"]:
            stats["best_win_streak"] = stats["current_streak"]
    else:
        stats["losses"] += 1
        if stats["streak_type"] == "loss":
            stats["current_streak"] += 1
        else:
            stats["current_streak"] = 1
            stats["streak_type"] = "loss"
    
    stats["win_rate"] = (stats["wins"] / stats["total_matches"]) * 100 if stats["total_matches"] > 0 else 0.0
    
    await db.stats.update_one(
        {"user_id": user_id, "group_id": group_id},
        {"$set": stats},
        upsert=True
    )

# ===== AUTHENTICATION ROUTES =====

@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check if username exists
    existing_username = await db.users.find_one({"username": user_data.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Create user
    user_dict = {
        "email": user_data.email,
        "username": user_data.username,
        "password": get_password_hash(user_data.password),
        "avatar": None,
        "bio": None,
        "favorite_games": [],
        "external_accounts": {},
        "created_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    # Create token
    access_token = create_access_token(data={"sub": str(result.inserted_id)})
    
    user_profile = UserProfile(
        id=str(result.inserted_id),
        email=user_dict["email"],
        username=user_dict["username"],
        avatar=user_dict["avatar"],
        bio=user_dict["bio"],
        favorite_games=user_dict["favorite_games"],
        external_accounts=user_dict["external_accounts"],
        created_at=user_dict["created_at"]
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_profile)

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    
    user_profile = UserProfile(
        id=str(user["_id"]),
        email=user["email"],
        username=user["username"],
        avatar=user.get("avatar"),
        bio=user.get("bio"),
        favorite_games=user.get("favorite_games", []),
        external_accounts=user.get("external_accounts", {}),
        created_at=user["created_at"]
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_profile)

@api_router.get("/auth/me", response_model=UserProfile)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserProfile(
        id=str(current_user["_id"]),
        email=current_user["email"],
        username=current_user["username"],
        avatar=current_user.get("avatar"),
        bio=current_user.get("bio"),
        favorite_games=current_user.get("favorite_games", []),
        external_accounts=current_user.get("external_accounts", {}),
        created_at=current_user["created_at"]
    )

# ===== USER ROUTES =====

@api_router.put("/users/profile", response_model=UserProfile)
async def update_profile(user_update: UserUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}
    
    if "username" in update_data:
        existing = await db.users.find_one({
            "username": update_data["username"],
            "_id": {"$ne": current_user["_id"]}
        })
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": update_data}
    )
    
    updated_user = await db.users.find_one({"_id": current_user["_id"]})
    
    return UserProfile(
        id=str(updated_user["_id"]),
        email=updated_user["email"],
        username=updated_user["username"],
        avatar=updated_user.get("avatar"),
        bio=updated_user.get("bio"),
        favorite_games=updated_user.get("favorite_games", []),
        external_accounts=updated_user.get("external_accounts", {}),
        created_at=updated_user["created_at"]
    )

@api_router.get("/users/{user_id}", response_model=UserProfile)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserProfile(
            id=str(user["_id"]),
            email=user["email"],
            username=user["username"],
            avatar=user.get("avatar"),
            bio=user.get("bio"),
            favorite_games=user.get("favorite_games", []),
            external_accounts=user.get("external_accounts", {}),
            created_at=user["created_at"]
        )
    except:
        raise HTTPException(status_code=404, detail="User not found")

# ===== GROUP ROUTES =====

@api_router.post("/groups", response_model=Group)
async def create_group(group_data: GroupCreate, current_user: dict = Depends(get_current_user)):
    group_dict = {
        "name": group_data.name,
        "icon": group_data.icon,
        "description": group_data.description,
        "owner_id": str(current_user["_id"]),
        "members": [str(current_user["_id"])],
        "created_at": datetime.utcnow()
    }
    
    result = await db.groups.insert_one(group_dict)
    group_dict["_id"] = result.inserted_id
    
    # Create activity
    await create_activity(
        str(result.inserted_id),
        str(current_user["_id"]),
        current_user["username"],
        "group_created",
        f"{current_user['username']} created the group"
    )
    
    return Group(
        id=str(result.inserted_id),
        name=group_dict["name"],
        icon=group_dict["icon"],
        description=group_dict["description"],
        owner_id=group_dict["owner_id"],
        members=group_dict["members"],
        created_at=group_dict["created_at"]
    )

@api_router.get("/groups", response_model=List[Group])
async def get_user_groups(current_user: dict = Depends(get_current_user)):
    groups = await db.groups.find({"members": str(current_user["_id"])}).limit(100).to_list(100)
    return [Group(
        id=str(g["_id"]),
        name=g["name"],
        icon=g.get("icon"),
        description=g.get("description"),
        owner_id=g["owner_id"],
        members=g["members"],
        created_at=g["created_at"]
    ) for g in groups]

@api_router.get("/groups/{group_id}", response_model=Group)
async def get_group(group_id: str, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    return Group(
        id=str(group["_id"]),
        name=group["name"],
        icon=group.get("icon"),
        description=group.get("description"),
        owner_id=group["owner_id"],
        members=group["members"],
        created_at=group["created_at"]
    )

@api_router.put("/groups/{group_id}", response_model=Group)
async def update_group(group_id: str, group_update: GroupUpdate, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if group["owner_id"] != str(current_user["_id"]):
        raise HTTPException(status_code=403, detail="Only group owner can update")
    
    update_data = {k: v for k, v in group_update.dict().items() if v is not None}
    
    await db.groups.update_one(
        {"_id": ObjectId(group_id)},
        {"$set": update_data}
    )
    
    updated_group = await db.groups.find_one({"_id": ObjectId(group_id)})
    
    return Group(
        id=str(updated_group["_id"]),
        name=updated_group["name"],
        icon=updated_group.get("icon"),
        description=updated_group.get("description"),
        owner_id=updated_group["owner_id"],
        members=updated_group["members"],
        created_at=updated_group["created_at"]
    )

@api_router.post("/groups/{group_id}/join")
async def join_group(group_id: str, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) in group["members"]:
        raise HTTPException(status_code=400, detail="Already a member")
    
    await db.groups.update_one(
        {"_id": ObjectId(group_id)},
        {"$push": {"members": str(current_user["_id"])}}
    )
    
    # Create activity
    await create_activity(
        group_id,
        str(current_user["_id"]),
        current_user["username"],
        "member_joined",
        f"{current_user['username']} joined the group 👋"
    )
    
    return {"message": "Joined group successfully"}

@api_router.get("/groups/{group_id}/members", response_model=List[UserProfile])
async def get_group_members(group_id: str, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    # Bulk query instead of N+1 pattern
    member_ids = [ObjectId(mid) for mid in group["members"]]
    users = await db.users.find({"_id": {"$in": member_ids}}).to_list(len(member_ids))
    
    members = []
    for user in users:
        members.append(UserProfile(
            id=str(user["_id"]),
            email=user["email"],
            username=user["username"],
            avatar=user.get("avatar"),
            bio=user.get("bio"),
            favorite_games=user.get("favorite_games", []),
            external_accounts=user.get("external_accounts", {}),
            created_at=user["created_at"]
        ))
    
    return members

# ===== GAME TYPE ROUTES =====

@api_router.post("/groups/{group_id}/game-types", response_model=GameType)
async def create_game_type(group_id: str, game_data: GameTypeCreate, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    game_dict = {
        "name": game_data.name,
        "icon": game_data.icon,
        "group_id": group_id,
        "created_at": datetime.utcnow()
    }
    
    result = await db.game_types.insert_one(game_dict)
    
    return GameType(
        id=str(result.inserted_id),
        name=game_dict["name"],
        icon=game_dict["icon"],
        group_id=game_dict["group_id"],
        created_at=game_dict["created_at"]
    )

@api_router.get("/groups/{group_id}/game-types", response_model=List[GameType])
async def get_game_types(group_id: str, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    game_types = await db.game_types.find({"group_id": group_id}).limit(100).to_list(100)
    return [GameType(
        id=str(gt["_id"]),
        name=gt["name"],
        icon=gt.get("icon"),
        group_id=gt["group_id"],
        created_at=gt["created_at"]
    ) for gt in game_types]

# ===== MATCH ROUTES =====

@api_router.post("/matches", response_model=Match)
async def create_match(match_data: MatchCreate, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(match_data.group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    match_dict = {
        "game_type_id": match_data.game_type_id,
        "group_id": match_data.group_id,
        "date": match_data.date,
        "players": match_data.players,
        "winner_ids": match_data.winner_ids,
        "score": match_data.score,
        "notes": match_data.notes,
        "created_by": str(current_user["_id"]),
        "created_at": datetime.utcnow()
    }
    
    result = await db.matches.insert_one(match_dict)
    
    # Update stats for all players
    for player_id in match_data.players:
        is_winner = player_id in match_data.winner_ids
        await update_user_stats(player_id, match_data.group_id, is_winner)
    
    # Get game type name
    game_type = await db.game_types.find_one({"_id": ObjectId(match_data.game_type_id)})
    game_name = game_type["name"] if game_type else "Unknown Game"
    
    # Bulk query for winner names instead of N+1
    winner_ids_obj = [ObjectId(wid) for wid in match_data.winner_ids]
    winners = await db.users.find({"_id": {"$in": winner_ids_obj}}).to_list(len(winner_ids_obj))
    winner_names = [user["username"] for user in winners]
    
    winners_str = ", ".join(winner_names)
    await create_activity(
        match_data.group_id,
        str(current_user["_id"]),
        current_user["username"],
        "match_added",
        f"New {game_name} match: {winners_str} won! 🎮"
    )
    
    return Match(
        id=str(result.inserted_id),
        game_type_id=match_dict["game_type_id"],
        group_id=match_dict["group_id"],
        date=match_dict["date"],
        players=match_dict["players"],
        winner_ids=match_dict["winner_ids"],
        score=match_dict["score"],
        notes=match_dict["notes"],
        created_by=match_dict["created_by"],
        created_at=match_dict["created_at"]
    )

@api_router.get("/groups/{group_id}/matches", response_model=List[Match])
async def get_group_matches(group_id: str, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    matches = await db.matches.find({"group_id": group_id}).sort("date", -1).limit(50).to_list(50)
    return [Match(
        id=str(m["_id"]),
        game_type_id=m["game_type_id"],
        group_id=m["group_id"],
        date=m["date"],
        players=m["players"],
        winner_ids=m["winner_ids"],
        score=m.get("score"),
        notes=m.get("notes"),
        created_by=m["created_by"],
        created_at=m["created_at"]
    ) for m in matches]

# ===== LEADERBOARD ROUTES =====

@api_router.get("/groups/{group_id}/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(group_id: str, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    stats = await db.stats.find({"group_id": group_id}).sort("wins", -1).limit(50).to_list(50)
    
    # Bulk query for users instead of N+1
    user_ids = [ObjectId(stat["user_id"]) for stat in stats]
    users = await db.users.find({"_id": {"$in": user_ids}}).to_list(len(user_ids))
    user_dict = {str(user["_id"]): user for user in users}
    
    leaderboard = []
    for stat in stats:
        user = user_dict.get(stat["user_id"])
        if user:
            leaderboard.append(LeaderboardEntry(
                user_id=stat["user_id"],
                username=user["username"],
                avatar=user.get("avatar"),
                total_matches=stat["total_matches"],
                wins=stat["wins"],
                losses=stat["losses"],
                win_rate=stat["win_rate"],
                current_streak=stat["current_streak"],
                streak_type=stat["streak_type"]
            ))
    
    return leaderboard

@api_router.get("/groups/{group_id}/stats/{user_id}", response_model=UserStats)
async def get_user_stats(group_id: str, user_id: str, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    stats = await db.stats.find_one({"user_id": user_id, "group_id": group_id})
    
    if not stats:
        return UserStats(
            user_id=user_id,
            group_id=group_id,
            total_matches=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            current_streak=0,
            streak_type="none",
            best_win_streak=0
        )
    
    return UserStats(**stats)

# ===== MESSAGE ROUTES =====

@api_router.get("/groups/{group_id}/messages", response_model=List[Message])
async def get_messages(group_id: str, limit: int = 50, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    messages = await db.messages.find({"group_id": group_id}).sort("created_at", -1).limit(limit).to_list(limit)
    messages.reverse()  # Return oldest first
    
    return [Message(
        id=str(m["_id"]),
        group_id=m["group_id"],
        user_id=m["user_id"],
        username=m["username"],
        avatar=m.get("avatar"),
        content=m["content"],
        created_at=m["created_at"]
    ) for m in messages]

# ===== ACTIVITY ROUTES =====

@api_router.get("/groups/{group_id}/activities", response_model=List[Activity])
async def get_activities(group_id: str, limit: int = 50, current_user: dict = Depends(get_current_user)):
    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if str(current_user["_id"]) not in group["members"]:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    
    activities = await db.activities.find({"group_id": group_id}).sort("created_at", -1).limit(limit).to_list(limit)
    
    return [Activity(
        id=str(a["_id"]),
        group_id=a["group_id"],
        user_id=a["user_id"],
        username=a["username"],
        activity_type=a["activity_type"],
        description=a["description"],
        created_at=a["created_at"]
    ) for a in activities]

# ===== SOCKET.IO EVENTS =====

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

@sio.event
async def join_group(sid, data):
    """Join a group room for real-time updates"""
    group_id = data.get('group_id')
    if group_id:
        sio.enter_room(sid, group_id)
        logger.info(f"Client {sid} joined group {group_id}")

@sio.event
async def leave_group(sid, data):
    """Leave a group room"""
    group_id = data.get('group_id')
    if group_id:
        sio.leave_room(sid, group_id)
        logger.info(f"Client {sid} left group {group_id}")

@sio.event
async def send_message(sid, data):
    """Handle incoming chat messages"""
    try:
        group_id = data.get('group_id')
        user_id = data.get('user_id')
        content = data.get('content')
        
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return
        
        message = {
            "group_id": group_id,
            "user_id": user_id,
            "username": user["username"],
            "avatar": user.get("avatar"),
            "content": content,
            "created_at": datetime.utcnow()
        }
        
        result = await db.messages.insert_one(message)
        message["_id"] = result.inserted_id
        
        # Broadcast to group
        await sio.emit('new_message', serialize_doc(message), room=group_id)
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
