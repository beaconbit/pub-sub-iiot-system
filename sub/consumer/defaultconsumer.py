import pprint
import threading
import time
import asyncio
import nats
from dataclasses import dataclass
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

@dataclass
class LastSeenInfo:
    timestamp: int
    value: int

class DefaultConsumerThread(threading.Thread):
    def __init__(self, config, queue):
        super().__init__()
        self.daemon = True
        self.config = config
        self.queue = queue
        self.loop = asyncio.new_event_loop()
        self.nc = None
        self.js = None
        self._started = threading.Event() # this is a thread safe flag
        self._running = threading.Event() # this is a thread safe flag
        self.last_seen: dict[str, list(LastSeenInfo)] = {}

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

        # logger.info("Connected to NATS JetStream")

        # Create a durable consumer on 'device.*'
        attempt_reconnect = True
        attempt = 0
        backoff_in_seconds = 1
        while attempt_reconnect:
            logger.info(f"attempting to connect to nats-jetstream")
            try:
                await self.js.subscribe(
                    "device.>",
                    durable="device_consumer",
                    cb=self._handle_message,
                    manual_ack=True,
                    deliver_policy="all"  # or "new" depending on intent
                )
                await asyncio.sleep(5)
                attempt_reconnect = False
            except Exception as e:
                attempt += 1
                if backoff_in_seconds < 12:
                    backoff_in_seconds += 2
                await asyncio.sleep(backoff_in_seconds)
                attempt_reconnect = True
                logger.error(f"connection to nats-jetstream failed, attempt reconnect: {attempt_reconnect}, attempt: {attempt}")
                logger.exception(e)

    async def _close(self):
        # logger.info("Closing NATS connection...")
        if self.nc:
            await self.nc.drain()
            await self.nc.close()

    def stop(self):
        # logger.info("Stopping consumer...")
        self._running.clear()
        def _stop_loop():
            # logger.info("Shutting down event loop...")
            self.loop.stop()
        # Signal the loop to stop
        self.loop.call_soon_threadsafe(_stop_loop)

    def default_last_seen_list(self):
        # returns a list of length 8, containing LastSeenInfo objects
        return [LastSeenInfo(timestamp=0, value=0) for _ in range(8)]

    def add_last_seen_entry(self, key):
        if key in self.last_seen:
            return
        else:
            self.last_seen[key] = self.default_last_seen_list()

    def get_last_seen_entry(self, key):
        if key not in self.last_seen:
            self.add_last_seen_entry(key)
        return self.last_seen.get(key)
    
    def reset_last_seen_entry(self, key):
        self.last_seen[key] = self.default_last_seen_list()

    async def _handle_message(self, msg):
        if not self._running.is_set():
            return  # skip processing if we're shutting down
        try:
            subject = msg.subject
            full_msg = TelemetryMessage.from_bytes(msg.data)
            index = full_msg.data_field_index
            current_msg = LastSeenInfo(timestamp=full_msg.timestamp, value=full_msg.value)

            last_msg = self.get_last_seen_entry(subject)[index]

            payload = 0

            if current_msg.timestamp > last_msg.timestamp and current_msg.value < last_msg.value:
                self.reset_last_seen_entry(subject)
                self.get_last_seen_entry(subject)[index] = current_msg # even if current_msg.value is negative it's fine

            if current_msg.timestamp > last_msg.timestamp and current_msg.value > last_msg.value:
                payload = current_msg.value - last_msg.value

            self.get_last_seen_entry(subject)[index] = current_msg # even if payload is zero update the timestamp
            # logger.info(f"last message - TelemetryMessage:\n{pprint.pformat(vars(last_msg))}")
            # logger.info(f"current message - TelemetryMessage:\n{pprint.pformat(vars(current_msg))}")

            if payload > 0:
                logger.info(f"\npayload: {payload}\n")
                full_msg.value = payload
                logger.info(f"POSTING TO QUEUE - TelemetryMessage:\n{pprint.pformat(vars(full_msg))}")
                self.queue.put(full_msg)  # Put structured object on the queue
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


#session = SessionLocal()
#snapshot_repo = SnapshotRepository(session)
#consumer_name = "default"
#snapshot_repo.add_snapshot(consumer_name)
#snapshot_repo.get_snapshot(consumer_name)
#snapshot_repo.update_snapshot(consumer_name, int(time.time()))
#session.close()

