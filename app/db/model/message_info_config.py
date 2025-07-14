from sqlalchemy import Column, String, Integer, Boolean, Text, BigInteger, PrimaryKeyConstraint
from db.model.base import Base

class MessageInfoConfig(Base):
    __tablename__ = 'message_info_config'

    mac = Column(String, nullable=False)
    data_field_index = Column(Integer, nullable=False)
    ip = Column(String, nullable=False)
    source_name = Column(String)
    zone = Column(String)
    machine = Column(String)
    machine_stage = Column(String)
    event_type = Column(String)
    units = Column(String)
    pieces = Column(Integer)
    estimated_pieces = Column(Integer)
    rfid = Column(String)

    __table_args__ = (
        PrimaryKeyConstraint('mac', 'data_field_index'),
    )
