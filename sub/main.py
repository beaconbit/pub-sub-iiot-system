# main.py
import threading
import time
from utils.logging import setup_logger
from config import load_config
from consumer.defaultconsumer import DefaultConsumerThread

logger = setup_logger(__name__)

def main():
    # Load config
    config = load_config()
    logger.info("Loaded config:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")

    default_consumer = DefaultConsumerThread(config=config)
    default_consumer.start_and_wait()
    logger.info("default consumer started")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        default_consumer.stop()
        default_consumer.join()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()

