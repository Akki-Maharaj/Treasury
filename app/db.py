import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables early so DB connection string is picked up
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_URL = f"sqlite:///{BASE_DIR / 'treasury.db'}"

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or "postgresql" not in DATABASE_URL:
    DATABASE_URL = DEFAULT_SQLITE_URL

# PostgreSQL and SQLite need slightly different connection arguments
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# FastAPI dependency: yields a scoped DB session per request and guarantees cleanup
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
