# main.py
import threading
import time
from utils.logging import setup_logger
from config import load_config
from master.scanner import ScannerThread
from master.watcher import WatcherThread
from master.device_registry import DeviceRegistry  
from master.device_registry import set_registry  # Singleton instance

logger = setup_logger(__name__)

class ProfiledLock:
    def __init__(self):
        self._lock = threading.Lock()
        self._wait_start = None
        self._hold_start = None

    def acquire(self, blocking=True, timeout=-1):
        thread_name = threading.current_thread().name
        self._wait_start = time.perf_counter()
        acquired = self._lock.acquire(blocking, timeout)
        self._hold_start = time.perf_counter()
        wait_time = self._hold_start - self._wait_start
        logger.critical(f"[{thread_name}] Lock waited {wait_time:.6f}s")
        return acquired

    def release(self):
        held_time = time.perf_counter() - self._hold_start
        logger.critical(f"Lock held {held_time:.6f}s")
        self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

def main():
    logger.info("Starting network scanner system")

    # Load config
    config = load_config()
    logger.info("Loaded config:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")

    # Store config in registry 
    if config.get("process", {}).get("mode") == "debug":
        lock = ProfiledLock()
    else:
        lock = threading.Lock()
    singleton_instance = DeviceRegistry(lock=lock, config=config)
    set_registry(singleton_instance)

    # Start scanner thread
    scanner = ScannerThread(config=config)
    scanner.daemon = True
    scanner.start()
    logger.info("Scanner thread started")

    # Start watcher thread (manages per-device threads)
    watcher = WatcherThread(config=config)
    watcher.daemon = True
    watcher.start()
    logger.info("Watcher thread started")

    # Keep main thread alive (Ctrl+C to exit)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scanner.stop()
        watcher.stop()
        scanner.join()
        watcher.join()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()

