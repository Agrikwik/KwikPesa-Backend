import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

# Render/SQLAlchemy fix for 'postgres://' vs 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    # --- ADD THESE THREE LINES ---
    pool_size=10,
    max_overflow=20,
    pool_recycle=300, # Discard connections older than 5 mins
    pool_pre_ping=True # Checks if connection is alive before using it
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)