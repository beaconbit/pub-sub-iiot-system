from db.model.message_info_config import MessageInfoConfig
from utils.logging import setup_logger

logger = setup_logger(__name__)


class MessageInfoConfigRepository:
    def __init__(self, session):
        self.session = session

    def get_all(self):
        return self.session.query(MessageInfoConfig).all()

    def get_by_mac(self, mac):
        return self.session.query(MessageInfoConfig).filter_by(mac=mac).all()

    def get_by_mac_and_index(self, mac, index):
        return self.session.query(MessageInfoConfig).filter_by(mac=mac, data_field_index=index).first()

