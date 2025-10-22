import os
import sqlite3
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
import hashlib
from core.constants import BASE_DIR

SECURITY = HTTPBearer()

# Paths
USER_DB_PATH = os.path.join(BASE_DIR, 'database', 'customer_data', 'loan_user_db.sqlite')
JWT_SECRET_FILE = os.path.join(BASE_DIR, 'database', 'customer_data', '.jwt_secret')

# Admin creds (read from env)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ADMIN_JWT_KEY = os.getenv('ADMIN_JWT_KEY')


def _load_jwt_secret() -> str:
    if os.path.exists(JWT_SECRET_FILE):
        with open(JWT_SECRET_FILE, 'r') as fh:
            return fh.read().strip()
    raise RuntimeError('JWT secret not found; run create_user_db script first')


def _verify_user_token(token: str) -> Optional[Dict[str, Any]]:
    secret = _load_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        # payload should contain 'sub' = customer_id
        return {'role': 'user', 'sub': payload.get('sub'), 'raw': payload}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token expired')
    except jwt.InvalidTokenError:
        return None


def _verify_admin_token(token: str) -> Optional[Dict[str, Any]]:
    if not ADMIN_JWT_KEY:
        return None
    try:
        payload = jwt.decode(token, ADMIN_JWT_KEY, algorithms=['HS256'])
        return {'role': 'admin', 'sub': payload.get('sub'), 'raw': payload}
    except Exception:
        return None


def authenticate(credentials: HTTPAuthorizationCredentials = Security(SECURITY)) -> Dict[str, Any]:
    """FastAPI dependency to authenticate requests. Returns context dict with role and subject."""
    scheme = credentials.scheme
    token = credentials.credentials
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=401, detail='Invalid auth scheme')

    # Try admin first
    admin_ok = _verify_admin_token(token)
    if admin_ok:
        return admin_ok

    user_ok = _verify_user_token(token)
    if user_ok:
        return user_ok

    raise HTTPException(status_code=401, detail='Invalid or expired token')
