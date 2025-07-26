from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import load_config

# Load config
config = load_config()
DATABASE_URL = config.get("process", {}).get("db_url", "sqlite:///db/data/devices.db")

engine = create_engine(
        DATABASE_URL, 
        echo=False, 
        pool_size=50,          # default is 5
        max_overflow=10,       # default is 10 (allows 10 more connections above pool_size)
        pool_timeout=30,       # seconds to wait before giving up if pool is exhausted
        pool_recycle=1800,      # optional: refresh stale connections every 30 mins
        future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


