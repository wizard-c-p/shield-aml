from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite Database URL. 
# For Production, replace this with a PostgreSQL URL.
DB_URL = "sqlite:///./shield_aml.db"

# Create the database engine
# check_same_thread=False is required only for SQLite
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

# Create a Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()