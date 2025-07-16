from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import load_config

# Load config
config = load_config()
DATABASE_URL = config.get("process", {}).get("db_url", "sqlite:///db/data/devices.db")

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


