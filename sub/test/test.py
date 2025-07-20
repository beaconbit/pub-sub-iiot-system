import threading
import time
import asyncio
from utils.logging import setup_logger

logger = setup_logger(__name__)

class TestThread(threading.Thread):
    def __init__(self, queue):
        super().__init__()
        self.daemon = True
        self.queue = queue
        self.loop = asyncio.new_event_loop()
        self._started = threading.Event() # this is a thread safe flag
        self._running = threading.Event() # this is a thread safe flag

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start())
        self._started.set()
        self._running.set()
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self._close())
            self.loop.close()
    
    def start_and_wait(self):
        logger.info("TEST start and wait call")
        self.start()
        self._started.wait()

    async def _start(self):
        # TODO make this url a config parameter

        logger.info("TEST started")


    async def _close(self):
        logger.info("TEST _close called")

    def stop(self):
        logger.info("TEST stop called")
        self._running.clear()
        def _stop_loop():
            # logger.info("Shutting down event loop...")
            self.loop.stop()
        # Signal the loop to stop
        self.loop.call_soon_threadsafe(_stop_loop)


