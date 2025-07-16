import pprint
import threading
import time
import asyncio
import nats
from db.utils.db_session import SessionLocal
from db.repository.snapshot_repository import SnapshotRepository
from utils.logging import setup_logger
from utils.message import TelemetryMessage
from utils.message import Product
from utils.message import Zone
from utils.message import Machine
from utils.message import MachineStage
from utils.message import EventType

logger = setup_logger(__name__)

class DefaultConsumerThread(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.daemon = True
        self.config = config
        self.loop = asyncio.new_event_loop()
        self.nc = None
        self.js = None
        self._started = threading.Event() # this is a thread safe flag
        self._running = threading.Event() # this is a thread sage flag

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
        self.start()
        self._started.wait()

    async def _start(self):
        # TODO make this url a config parameter
        self.nc = await nats.connect("nats://nats:4222")
        self.js = self.nc.jetstream()

        logger.info("Connected to NATS JetStream")

        # Create a durable consumer on 'device.*'
        await self.js.subscribe(
            "device.>",
            durable="device_consumer",
            cb=self._handle_message,
            manual_ack=True,
            deliver_policy="all"  # or "new" depending on intent
        )
        logger.info("Subscribed to 'device.*'")

    async def _handle_message(self, msg):
        if not self._running.is_set():
            return  # skip processing if we're shutting down
        try:
            subject = msg.subject
            telemetry = TelemetryMessage.from_bytes(msg.data)
            logger.info(f"Received on subject: {subject} - TelemetryMessage:\n{pprint.pformat(vars(telemetry))}")
            await msg.ack()
        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON from TelemetryMessage:")
            logger.error(repr(msg.data))
            logger.exception(e)
        except ValueError as e:
            logger.error("Invalid enum or field in TelemetryMessage.")
            logger.error(repr(msg.data))
            logger.exception(e)
        except Exception as e:
            logger.error("Unexpected error while processing message.")
            logger.error(repr(msg.data))
            logger.exception(e)

    async def _close(self):
        logger.info("Closing NATS connection...")
        if self.nc:
            await self.nc.drain()
            await self.nc.close()

    def stop(self):
        logger.info("Stopping consumer...")
        self._running.clear()
        def _stop_loop():
            logger.info("Shutting down event loop...")
            self.loop.stop()
        # Signal the loop to stop
        self.loop.call_soon_threadsafe(_stop_loop)

#session = SessionLocal()
#snapshot_repo = SnapshotRepository(session)
#consumer_name = "default"
#snapshot_repo.add_snapshot(consumer_name)
#snapshot_repo.get_snapshot(consumer_name)
#snapshot_repo.update_snapshot(consumer_name, int(time.time()))
#session.close()

