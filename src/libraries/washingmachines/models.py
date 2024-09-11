from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class MachineState(Enum):
    AVAILABLE = "0"
    IN_SERVICE = "1"


class MachineInformations(BaseModel):
    serial_number: str
    machine_in_service: bool
    machine_name: str
    machine_nbr: int
    machine_price: int
    machine_state: MachineState
    machine_type: str
    detail: Any
    duration_estimate: Any
    special_val: Any
    date_time: datetime
    is_fictive_occupation: bool
    machine_state_fictive: bool
    started_at: datetime | None
