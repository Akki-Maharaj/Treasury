import os
import uuid
import bcrypt
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User

# Fallback secret key for session cookies if not supplied in .env
SECRET_KEY = os.getenv("SECRET_KEY", "treasury-super-secret-session-key-32chars")


# Hashes raw password string with a salt using bcrypt
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# Validates a raw password against its stored bcrypt hash
def check_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# Depends() injects the current DB session and extracts user from session cookie
def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id_raw = request.session.get("user_id")
    if not user_id_raw:
        return None
    try:
        return db.query(User).filter(User.id == int(user_id_raw)).first()
    except (ValueError, TypeError):
        return None


# Enforces authentication by checking session and redirecting unauthenticated users to login
def require_login(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": f"/login?next={request.url.path}"}
        )
    return user
