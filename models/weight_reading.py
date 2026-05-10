from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto


class WeightStatus(Enum):
    STABLE = auto()
    DYNAMIC = auto()
    OVER_RANGE = auto()
    UNDER_RANGE = auto()
    IN_PROGRESS = auto()
    ERROR = auto()


STATUS_LABELS = {
    WeightStatus.STABLE: "Stabilna",
    WeightStatus.DYNAMIC: "Dynamiczna",
    WeightStatus.OVER_RANGE: "Przekroczony zakres",
    WeightStatus.UNDER_RANGE: "Poniżej zakresu",
    WeightStatus.IN_PROGRESS: "W trakcie...",
    WeightStatus.ERROR: "Błąd",
}


@dataclass
class WeightReading:
    value: float
    unit: str
    status: WeightStatus
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]

    @property
    def formatted_value(self) -> str:
        return f"{self.value:.3f} {self.unit}"
