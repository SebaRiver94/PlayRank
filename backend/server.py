"""PlayRank API entrypoint.

`app` is the ASGI application served by uvicorn (server:app). It wraps the FastAPI
REST API and the Socket.IO server, which is exposed under /api/socket.io so it is
reachable through the same ingress as the REST API.
"""
import logging

import socketio
from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.config import CORS_ORIGINS, CORS_ORIGIN_REGEX
from core.db import client
from migrations.startup import run_startup_migrations
from realtime.socket import sio
from routers import auth, game_types, groups, matches, rankings, social, users

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

api = FastAPI(title="PlayRank API")

api_router = APIRouter(prefix="/api")


@api_router.get("/health")
async def health():
    return {"status": "ok"}


for module in (auth, users, groups, game_types, matches, rankings, social):
    api_router.include_router(module.router)

api.include_router(api_router)

api.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=False,  # auth uses Bearer tokens, not cookies
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@api.on_event("startup")
async def startup():
    await run_startup_migrations()


@api.on_event("shutdown")
async def shutdown_db_client():
    client.close()


app = socketio.ASGIApp(sio, other_asgi_app=api, socketio_path="api/socket.io")
