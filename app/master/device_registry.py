# global/device_registry.py

from db.utils.db_session import SessionLocal
from db.repository.device_repository import DeviceRepository
import threading
from utils.logging import setup_logger
from typing import Optional



logger = setup_logger(__name__)

_lock_type = type(threading.Lock())


class DeviceRegistry:
    def __init__(self, lock: threading.Lock, config: dict):
        if not (hasattr(lock, "acquire") and callable(lock.acquire) and
                hasattr(lock, "release") and callable(lock.release)):
            raise TypeError(f"Expected lock to be a Lock-like object, got {type(lock).__name__}")
        if not isinstance(config, dict):
            raise TypeError(f"Expected config to be dict, got {type(config).__name__}")

        self._devices = {}  # key: mac, value: device dict
        self._lock = lock
        self._config = config

        session = SessionLocal()
        try:
            repo = DeviceRepository(session)
            devices = repo.get_all_devices()  # should return a list of Device ORM instances
            if devices:
                self._devices = {
                    device.mac: {
                        "mac": device.mac,
                        "ip": device.ip,
                        "valid": device.valid,
                        "failures": device.failures,
                        "username": device.username,
                        "password": device.password,
                        "cookie": device.cookie,
                        "cookie_expires": device.cookie_expires,
                        "auth_flow": device.auth_flow,
                        "scraper": device.scraper,
                        "last_data": device.last_data,
                        "last_seen": device.last_seen,
                    }
                    for device in devices
                }
        except Exception as e:
            logger.error(f"Failed to load devices from database: {e}")
        finally:
            session.close()

    def get_config(self):
        return self._config

    def add_or_update_device(self, mac, ip):
        with self._lock:
            if mac not in self._devices:
                device_data = {
                    'mac': mac,
                    'ip': ip,
                    'valid': True,
                    'failures': 0,
                    'username': None,
                    'password': None,
                    'cookie': None,
                    'cookie_expires': 0,
                    'auth_flow': None,
                    'scraper': None,
                    'last_data': None,
                    'last_seen': None,
                }
                self._devices[mac] = device_data


                session = SessionLocal()
                try:
                    repo = DeviceRepository(session)
                    repo.add_device(device_data)
                    logger.info(f"Persisted to database new device: {mac} @ {ip}")
                except Exception as e:
                    logger.error(f"Database could not persist new device: {mac} @ {ip}. Error: {e}")
                    session.rollback()  # optional but good practice on error
                finally:
                    session.close()
                logger.info(f"Added new device: {mac} @ {ip}")
            else:
                self._devices[mac]['ip'] = ip
                # TODO modify database entry
                logger.debug(f"Updated device IP: {mac} -> {ip}")

    def get_handle_to_self_invalidate(self, mac):
        def invalidate():
            with self._lock:
                if mac in self._devices:
                    self._devices[mac]['valid'] = False
                    logger.warning(f"Device marked invalid: {mac}")
                    # modify database entry
                    session = SessionLocal()
                    try:
                        repo = DeviceRepository(session)
                        kwargs = { 'valid' : False }
                        repo.update_device(mac, **kwargs)
                        logger.info(f"Invalidated database record for: {mac}")
                    except Exception as e:
                        logger.error(f"Database could not invalidate: {mac} . Error: {e}")
                        session.rollback()  
                    finally:
                        session.close()
        return invalidate

    def get_handle_to_self_validate(self, mac):
        def validate(password, username, auth_flow, scraper):
            with self._lock:
                if mac in self._devices:
                    self._devices[mac]['valid'] = True
                    self._devices[mac]['password'] = password
                    self._devices[mac]['username'] = username
                    self._devices[mac]['auth_flow'] = auth_flow
                    self._devices[mac]['scraper'] = scraper
                    logger.info(f"Device marked valid: {mac}")
                    # modify database entry
                    session = SessionLocal()
                    try:
                        repo = DeviceRepository(session)
                        kwargs = { 'valid' : True }
                        repo.update_device(mac, **kwargs)
                        logger.info(f"Validated database record for: {mac}")
                    except Exception as e:
                        logger.error(f"Database could not validate: {mac} . Error: {e}")
                        session.rollback()  
                    finally:
                        session.close()
        return validate

    def get_handle_to_update_device_field(self, mac):
        def update_device_field(**kwargs):
            with self._lock:
                if mac in self._devices:
                    for key, value in kwargs.items():
                        self._devices[mac][key] = value
                    # modify database entry
                    session = SessionLocal()
                    try:
                        repo = DeviceRepository(session)
                        repo.update_device(mac, **kwargs)
                        logger.info(f"Modified database record for {mac} fields {kwargs}")
                    except Exception as e:
                        logger.error(f"Database could not modify fields {kwargs} . Error: {e}")
                        session.rollback()  
                    finally:
                        session.close()
        return update_device_field

    def get_all_devices_copy(self):
        with self._lock:
            return list(self._devices.values())

    def get_device(self, mac):
        with self._lock:
            return self._devices.get(mac)

    def remove_device(self, mac):
        with self._lock:
            if mac in self._devices:
                del self._devices[mac]
                logger.info(f"Removed device: {mac}")

# This handles the singleton situation 
def set_registry(instance: DeviceRegistry):
    global registry
    registry = instance

def get_registry() -> DeviceRegistry:
    if registry is None:
        raise RuntimeError("DeviceRegistry has not been initialized yet. Call set_registry() first.")
    return registry

# this needs to be a singleton
registry: Optional[DeviceRegistry] = None
