"""
Authentication and Authorization module.
Provides password hashing via bcrypt, JWT token creation and verification,
and FastAPI dependencies for user authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

try:
    from .config import settings
    from .database import get_db
    from .models import User
    from .schemas import TokenData
except ImportError:
    from config import settings
    from database import get_db
    from models import User
    from schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/login",
    auto_error=False,
)


def hash_password(password: str) -> str:
    """
    Hashes a plain text password using bcrypt with automated salt generation.
    """
    # Truncate password to 72 bytes if needed to comply with bcrypt standard limit
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a bcrypt-hashed string.
    """
    try:
        pw_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a signed JWT access token containing the provided payload data.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decodes and validates a JWT token, returning the TokenData payload if valid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username)
    except (jwt.PyJWTError, ValueError):
        return None


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency requiring a valid JWT token.
    Raises HTTP 401 Unauthorized if token is missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    token_data = decode_access_token(token)
    if token_data is None or token_data.username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI dependency for optional authentication.
    Returns the User if a valid token is provided, or None if no token or invalid.
    Allows conversion endpoints to support both guests and logged-in users.
    """
    if not token:
        return None

    token_data = decode_access_token(token)
    if token_data is None or token_data.username is None:
        return None

    user = db.query(User).filter(User.username == token_data.username).first()
    if user and user.is_active:
        return user

    return None
