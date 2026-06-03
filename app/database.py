import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

logger = logging.getLogger("uvicorn.error")

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./expense_tracker.db")

# Render and some providers use "postgres://" — SQLAlchemy 2.x requires "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,       # detect stale connections before using them
        pool_size=5,              # keep 5 persistent connections
        max_overflow=10,          # allow up to 10 extra connections under load
        pool_timeout=30,          # raise after 30s if no connection is available
        pool_recycle=1800,        # recycle connections older than 30 min
        connect_args={"connect_timeout": 10},  # fail fast on unreachable host
    )

logger.info("Database engine created: %s", DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
