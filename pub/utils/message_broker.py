import asyncio
import threading
from asyncio import Queue
import nats
from utils.logging import setup_logger

logger = setup_logger(__name__)

class MessageBroker(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.queue = Queue()
        self.loop = asyncio.new_event_loop()
        self.nc = None
        self.js = None
        self._started = threading.Event()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start())
        self._started.set()
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self._close())
            self.loop.close()

    async def _start(self):
        self.nc = await nats.connect("nats://localhost:4222")
        self.js = self.nc.jetstream()
        await self.js.add_stream(name="device_stream", subjects=["device.>"])
        try:
            await self.js.add_stream(name="device_stream", subjects=["device.>"])
            logger.info("JetStream stream 'device_stream' created.")
        except Exception as e:
            if "stream name already in use" in str(e).lower():
                logger.info("JetStream stream 'device_stream' already exists.")
            else:
                logger.error(f"Error creating JetStream stream: {e}")
        asyncio.create_task(self._publish_worker())

    async def _close(self):
        await self.nc.drain()

    def start_and_wait(self):
        self.start()
        self._started.wait()  # Block until event loop is running

    def publish(self, subject: str, message: bytes):
        # Safe to call from any thread
        logger.info(f"trying to published to subject: {subject}, Message: {message}")
        asyncio.run_coroutine_threadsafe(self.queue.put((subject, message)), self.loop)

    async def _publish_worker(self):
        while True:
            subject, message = await self.queue.get()
            try:
                await self.js.publish(subject, message)
                logger.info(f"Published Message: {message}")
            except Exception as e:
                logger.error(f"Publish failed: {e}")

    def normalize_mac(self, mac: str) -> str:
        return mac.replace(":", "").lower()

    def get_handle_to_publisher(self, mac: str):
        norm_mac = self.normalize_mac(mac)
        subject = f"device.{norm_mac}"
        def publish_message(msg: bytes):
            self.publish(subject, msg)
        return publish_message

