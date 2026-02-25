import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
from base import Base

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load DATABASE_URL from environment or use default
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///oversite.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    """
    Initializes the local SQLite database and creates all defined tables.
    """
    import schema
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    Dependency for generating a new SQLAlchemy session.

    Yields:
        An active database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
