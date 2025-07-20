import threading
import time
import asyncio
from queue import Queue, Empty
from utils.logging import setup_logger
import psycopg
from dataclasses import asdict
from utils.message import TelemetryMessage

logger = setup_logger(__name__)

# TODO split some functionality into it's own class, _write_event should
# call eventlog_repository that handles actually writing to database
# and eventlog_repository itself should create an instance of PostgresSession
# which handles connecting to the database
class DBWriteThread(threading.Thread):
    def __init__(self, queue):
        super().__init__()
        self.daemon = True
        self.queue = queue
        self.loop = asyncio.new_event_loop()
        self._started = threading.Event()
        self._running = threading.Event()
        self.dsn = "postgresql://admin:password123@postgres:5432/eventlog"

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start())
        self.loop.create_task(self._run_loop())
        self._started.set()
        self._running.set()
        try: 
            self.loop.run_forever()
        finally: 
            self.loop.run_until_complete(self.close())
            self.loop.close()

    async def _run_loop(self):
        while self._running.is_set():
            try:
                with psycopg.connect(self.dsn, autocommit=False) as conn:
                    with conn.cursor() as cur:
                        while self._running.is_set():
                            try:
                                telemetry_msg = self.queue.get(timeout=1)
                                logger.info(f"DBWriteThread processing {telemetry_msg}")
                                if telemetry_msg is None:
                                    logger.info("Shutdown signal received")
                                    break

                                self._write_event(cur, telemetry_msg)
                                conn.commit()
                            except Empty:
                                continue
                            except Exception as e:
                                conn.rollback()
                                logger.error(f"DB write failed: {e}", exc_info=True)
            except Exception as e:
                logger.critical(f"Failed to connect to Postgres: {e}", exc_info=True)
        logger.info("DBWriteThread exiting cleanly")

    def _write_event(self, cur, telemetry_msg):
        logger.info(f"_write_event called with \n{cur} \n{telemetry_msg}")
        """
        Insert a telemetry event into the 'general' table.

        Required keys: timestamp, source_mac, source_ip
        Optional keys: all other columns in the table
        """
        # TODO move this logic into a to_dict(self) function on telemetry message
        event = asdict(telemetry_msg)
        for field in ["product", "zone", "machine", "machine_stage", "event_type"]:
            value = event.get(field)
            if value is not None and hasattr(value, "name"):
                event[field] = value.name
        # TODO end

        required_keys = {"timestamp", "source_mac", "source_ip"}
        all_columns = {
            "timestamp", "source_mac", "source_ip", "source_name", "value",
            "data_field_index", "product", "zone", "machine", "machine_stage",
            "event_type", "units", "pieces", "estimated_pieces", "rfid", "dry_time_seconds"
        }
        # Ensure required fields are present
        missing = {k for k in required_keys if not event.get(k)}
        if missing:
            raise ValueError(f"Missing required fields in event: {missing}")

        columns = [k for k in all_columns if event.get(k) is not None]
        placeholders = [f"%({col})s" for col in columns]
        sql = f"""
            INSERT INTO general ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
        """
        # Only pass the subset of event keys that aren't 'None'
        filtered_event = {k: event[k] for k in columns}
        logger.info(f"Calling cur.execute on \n{sql} \n{filtered_event} \nEND of cur.execute")
        cur.execute(sql, filtered_event)

    def start_and_wait(self):
        self.start()
        self._started.wait()

    async def _start(self):
        logger.info(f"DBWriter setup complete")

    async def _close(self):
        logger.info(f"Closing {__name__}")

    def stop(self):
        logger.info(f"Stopping {__name__}")
        self._running.clear()
        def _stop_loop():
            logger.info(f"Stopped {__name__}")
            self.loop.stop()
        self.loop.call_soon_threadsafe(_stop_loop)
        





    # def stop(self):
    #     self._running.clear()
    #     self.queue.put(None)  # poison pill

