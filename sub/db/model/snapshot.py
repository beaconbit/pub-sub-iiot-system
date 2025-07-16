from sqlalchemy import Column, String, Integer, Boolean, Text, BigInteger
from db.model.base import Base

class Snapshot(Base):
    __tablename__ = 'snapshot'

    consumer_name = Column(String, primary_key=True)
    timestamp = Column(BigInteger)  # Unix timestamp

