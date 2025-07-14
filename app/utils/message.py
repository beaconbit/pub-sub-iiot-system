from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional
import json

class Product(Enum):
    ACCOMODATIONSHEET = "accomodation sheet"
    TOWEL = "towel"
    HOSPITALSHEET = "hospital sheet"

class Zone(Enum):
    SORTING = "sorting"
    WASHING = "washing"
    FINISHING = "finishing"

class Machine(Enum):
    IRONER1 = "Ironer 1"
    IRONER2 = "Ironer 2"
    IRONER3 = "Ironer 3"

class MachineStage(Enum):
    FEEDER = "feeder"
    FOLDER = "folder" 
    STACKER = "stacker"

class EventType(Enum):
    PROCESSEDPIECE = "processedpiece"
    DROPPEDLOAD = "droppedload"
    BATCHWASHERFULLROTATION = "batchwasherfullrotation"
    BAGIDENTIFIED = "bagidentified"
    CONVEYORTRAVEL = "conveyortravel"
    PRESSLOADING = "pressloading"
    PRESSUNLOADING = "pressunloading"
    DRYERLOADING = "dryerloading"
    DRYERUNLOADING = "dryerunloading"

@dataclass
class TelemetryMessage:
    timestamp: int
    source_mac: str
    source_ip: str
    source_name: Optional[str] = None
    product: Optional[Product] = None
    zone: Optional[Zone] = None
    machine: Optional[Machine] = None
    machine_stage: Optional[MachineStage] = None
    event_type: Optional[EventType] = None
    units: Optional[str] = None
    value: Optional[int] = None
    data_field_index: Optional[int] = None
    pieces: Optional[int] = None
    estimated_pieces: Optional[int] = None
    rfid: Optional[str] = None
    dry_time_seconds: Optional[int] = None

    def to_bytes(self) -> bytes:
        # Convert Enums to values for serialization
        d = asdict(self)
        d.update({
            "product": self.product.value if self.product else None,
            "zone": self.zone.value if self.zone else None,
            "machine": self.machine.value if self.machine else None,
            "machine_stage": self.machine_stage.value if self.machine_stage else None,
            "event_type": self.event_type.value if self.event_type else None,
        })
        return json.dumps(d, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def from_bytes(data: bytes) -> "TelemetryMessage":
        d = json.loads(data.decode("utf-8"))
        return TelemetryMessage(
            timestamp=d["timestamp"],
            source_mac=d["source_mac"],
            source_ip=d["source_ip"],
            source_name=d.get("source_name"),
            product=Product(d.get("product")),
            zone=Zone(d.get("zone")),
            machine=Machine(d.get("machine")),
            machine_stage=MachineStage(d.get("machine_stage")),
            event_type=EventType(d.get("event_type")),
            units=d.get("units"),
            value=d.get("value"),
            data_field_index=d.get("data_field_index"),
            pieces=d.get("pieces"),
            estimated_pieces=d.get("estimated_pieces"),
            rfid=d.get("rfid"),
            dry_time_seconds=d.get("dry_time_seconds"),
        )

