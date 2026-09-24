"""Shared FastAPI dependencies: DB session, current-user resolution, admin gate."""

from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.db import get_db
from app.models.user import User

SESSION_COOKIE_NAME = "sez_session"

__all__ = ["SESSION_COOKIE_NAME", "get_db", "get_current_user", "require_admin"]


def get_current_user(
    sez_session: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    unauthenticated = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
    )
    if not sez_session:
        raise unauthenticated

    username = decode_access_token(sez_session)
    if not username:
        raise unauthenticated

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise unauthenticated
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
