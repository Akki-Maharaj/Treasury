import uuid
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.auth import hash_password, check_password, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# Renders signup page or redirects to home if already logged in
@router.get("/signup", response_class=HTMLResponse)
def get_signup(request: Request, current_user=Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="signup.html", context={"current_user": None})


# Handles user registration with email uniqueness check and password hashing
@router.post("/signup", response_class=HTMLResponse)
def post_signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    phone: str = Form(""),
    db: Session = Depends(get_db)
):
    clean_email = email.strip().lower()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={"current_user": None, "error": "Email is already registered. Please login."},
            status_code=400
        )

    new_user = User(
        name=name.strip(),
        email=clean_email,
        password_hash=hash_password(password),
        phone=phone.strip() or None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    request.session["user_id"] = str(new_user.id)
    return RedirectResponse(url="/", status_code=303)


# Renders login form or redirects home if already authenticated
@router.get("/login", response_class=HTMLResponse)
def get_login(request: Request, next: str = "/", current_user=Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"current_user": None, "next": next})


# Validates credentials and sets signed cookie session on success
@router.post("/login", response_class=HTMLResponse)
def post_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db)
):
    clean_email = email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not check_password(password, user.password_hash or ""):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"current_user": None, "error": "Invalid email or password", "next": next},
            status_code=400
        )

    request.session["user_id"] = str(user.id)
    target = next if next.startswith("/") else "/"
    return RedirectResponse(url=target, status_code=303)


# Clears session cookie to sign out the user
@router.get("/logout")
def get_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
