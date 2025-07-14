from sqlalchemy import Column, String, Integer, Boolean, Text, BigInteger
from db.model.base import Base

class Device(Base):
    __tablename__ = 'devices'

    mac = Column(String, primary_key=True)
    ip = Column(String, nullable=False)
    valid = Column(Boolean, default=True)
    failures = Column(Integer, default=0)
    username = Column(String)
    password = Column(String)
    cookie = Column(Text)
    cookie_expires = Column(BigInteger, default=0)  # Unix timestamp
    auth_flow = Column(String)
    scraper = Column(String)
    last_data = Column(Text)
    last_seen = Column(BigInteger)  # Unix timestamp

