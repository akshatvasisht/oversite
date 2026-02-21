import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load DATABASE_URL from environment or use default
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///maddata.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    # Import Base and models only here or implicitly via imported models
    from models import Base
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
