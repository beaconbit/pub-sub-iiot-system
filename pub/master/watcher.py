import threading
import time
from utils.logging import setup_logger
from device.worker import DeviceWorker
from master.device_registry import get_registry
from utils.message_broker import MessageBroker
import asyncio

logger = setup_logger(__name__)

class WatcherThread(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.daemon = True
        self.running = True
        self.check_interval = config.get("device_check_interval", 10)
        self.device_threads = {}  # type: dict[str, DeviceWorker]
        self.recheck_invalid_devices = False
        self.count_down_before_recheck = config.get("invalid_check_every_n_cycles", 360)
        self.count_down = self.count_down_before_recheck
        self.registry = None
        self.broker = MessageBroker()

    def run(self):
        logger.info("Watcher loop starting")
        self.registry = get_registry()
        self.broker.start_and_wait()
        while self.running:
            self.update_recheck_flag()
            self.manage_device_threads()
            self.recheck_invalid_devices = False
            time.sleep(self.check_interval)
            
    def update_recheck_flag(self):
        self.count_down -= 1
        if self.count_down <= 0:
            self.recheck_invalid_devices = True
            self.count_down = self.count_down_before_recheck

    def manage_device_threads(self):
# ************* ACCESS SHARED DEVICE REGISTRY ******************
        logger.info("Registry found")
        current_devices = self.registry.get_all_devices_copy()
        for device in current_devices:
            mac = device["mac"]
            logger.debug(f"Checking device {mac} is still valid")
            is_valid = device["valid"]
            if is_valid or self.recheck_invalid_devices:
                if mac not in self.device_threads:
                    validate = self.registry.get_handle_to_self_validate(mac)
                    invalidate = self.registry.get_handle_to_self_invalidate(mac)
                    update_device_field = self.registry.get_handle_to_update_device_field(mac)
                    publish = self.broker.get_handle_to_publisher(mac)
                    self.start_worker_for_device(
                        device, 
                        validate, 
                        invalidate, 
                        update_device_field, 
                        publish
                    )
            else: # kill threads that are no longer valid 
                logger.debug(f"Found Invalid Device {mac}. KILLING !!")
                if mac in self.device_threads:
                    logger.debug(f"Found Invalid Device {mac}.  REALLY KILLING IT !!")
                    self.stop_worker_for_device(mac)

    def stop(self):
        self.running = False

    # Individual device thread management
    def start_worker_for_device(self, device, validate, invalidate, update_device_field, publish):
        mac = device["mac"]
        thread = DeviceWorker(device, validate, invalidate, update_device_field, publish)
        thread.start()
        self.device_threads[mac] = thread

    def stop_worker_for_device(self, mac):
        thread = self.device_threads[mac]
        thread.stop()
        thread.join()
        del self.device_threads[mac]
        logger.debug(f"Found Invalid Device {mac}.  FINISHED KILLING IT !!")
        logger.debug(f"{self.device_threads}")
