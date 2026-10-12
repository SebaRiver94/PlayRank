import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('SECRET_KEY must be set in the environment')

JWT_ALGORITHM = 'HS256'
JWT_ISSUER = 'playrank-api'
JWT_AUDIENCE = 'playrank-app'
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '43200'))  # 30 days

CORS_ORIGINS = [
    o.strip() for o in os.environ.get('CORS_ORIGINS', '').split(',')
    if o.strip() and o.strip() != '*'
]
CORS_ORIGIN_REGEX = os.environ.get('CORS_ORIGIN_REGEX') or None
_origin_re = re.compile(CORS_ORIGIN_REGEX) if CORS_ORIGIN_REGEX else None

# Brute-force protection for login
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES_PER_EMAIL = 10
LOGIN_MAX_FAILURES_PER_IP = 30


def is_origin_allowed(origin) -> bool:
    if not origin:
        return False
    if origin in CORS_ORIGINS:
        return True
    return bool(_origin_re and _origin_re.match(origin))
