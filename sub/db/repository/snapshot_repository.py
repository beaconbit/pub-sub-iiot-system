from sqlalchemy.orm import Session
from db.model.snapshot import Snapshot
from utils.logging import setup_logger

logger = setup_logger(__name__)

class SnapshotRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_snapshot(self, consumer_name: str):
        snapshot = Snapshot(consumer_name, 0)
        self.session.add(snapshot)
        self.session.commit()

    def get_snapshot(self, consumer_name: str) -> Snapshot | None:
        return self.session.query(Snapshot).filter(Snapshot.consumer_name == consumer_name).first()

    def update_snapshot(self, consumer_name: str, timestamp: int):
        snapshot = self.get_snapshot(consumer_name)
        if snapshot:
            snapshot.timestamp = timestamp
            self.session.commit()

