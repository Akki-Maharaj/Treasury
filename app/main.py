import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import SECRET_KEY
from app.routes.auth_routes import router as auth_router
from app.routes.pages import router as pages_router
from app.routes.wishlist_routes import router as wishlist_router
from app.routes.sell_routes import router as sell_router
from app.routes.ai_routes import router as ai_router

# Initialize the main FastAPI application
app = FastAPI(title="Treasury Marketplace")

# SessionMiddleware signs session cookies with SECRET_KEY for tamper-proof auth
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="treasury_session",
    max_age=14 * 24 * 3600
)

# Mount static files and local seed-data images
BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "app" / "static"
seed_dir = BASE_DIR / "seed-data"

static_dir.mkdir(parents=True, exist_ok=True)
seed_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/seed-data", StaticFiles(directory=str(seed_dir)), name="seed_data")

# Register all application routes
app.include_router(auth_router)
app.include_router(pages_router)
app.include_router(wishlist_router)
app.include_router(sell_router)
app.include_router(ai_router)
