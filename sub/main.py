# main.py
import threading
import time
from utils.logging import setup_logger
from config import load_config
from queue import Queue
from consumer.defaultconsumer import DefaultConsumerThread
from writer.dbwritethread import DBWriteThread

logger = setup_logger(__name__)

def main():
    # Load config
    config = load_config()
    logger.info("Loaded config:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")

    # Create shared thread-safe queue consumers will place write-job's onto for 
    # DBWriteThread to process (write to database)
    event_queue = Queue()

    # Start DB write thread
    db_writer = DBWriteThread(queue=event_queue)
    db_writer.daemon = True
    db_writer.start_and_wait()
    logger.info(f"octopus DB write thread started ...")
    logger.info(f"octopus DB write thread started {db_writer.is_alive()}")

    default_consumer = DefaultConsumerThread(config=config, queue=event_queue)
    default_consumer.daemon = True
    default_consumer.start_and_wait()
    logger.info("default consumer started")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        default_consumer.stop()
        db_writer.stop()
        default_consumer.join()
        db_writer.join()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()

