import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Find database path in store_intelligence folder
DB_PATH = Path(__file__).resolve().parent.parent / "store_intelligence" / "anomalies.db"
# Ensure parent folder exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Safe for SQLite with FastAPI multi-threading
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for API endpoints to retrieve a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
