from sqlalchemy.orm import Session
from db.model.device import Device
from utils.logging import setup_logger

logger = setup_logger(__name__)

class DeviceRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_device(self, device_data: dict):
        device = Device(**device_data)
        self.session.add(device)
        self.session.commit()

    def get_device_by_mac(self, mac: str) -> Device | None:
        return self.session.query(Device).filter(Device.mac == mac).first()

    def update_device(self, mac: str, **kwargs):
        logger.info(f"Calling update device")
        device = self.get_device_by_mac(mac)
        if device:
            for key, value in kwargs.items():
                setattr(device, key, value)
            self.session.commit()

    def delete_device(self, mac: str):
        device = self.get_device_by_mac(mac)
        if device:
            self.session.delete(device)
            self.session.commit()


    def get_all_devices(self) -> list[Device]:
        return self.session.query(Device).all()


