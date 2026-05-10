from abc import ABC, abstractmethod
from models.weight_reading import WeightReading


class ScaleProtocol(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def weight_command(self) -> bytes: ...

    @property
    @abstractmethod
    def weight_immediate_command(self) -> bytes: ...

    @property
    @abstractmethod
    def tare_command(self) -> bytes: ...

    @property
    @abstractmethod
    def zero_command(self) -> bytes: ...

    @property
    @abstractmethod
    def default_baud_rate(self) -> int: ...

    @property
    def command_list(self) -> list[tuple[str, str]]:
        """Lista dostępnych komend: [(komenda_bez_CRLF, opis), ...]"""
        return []

    @abstractmethod
    def parse_response(self, line: str) -> WeightReading | None:
        """Parsuje jedną linię odpowiedzi z wagi. Zwraca None gdy linia jest niekompletna."""
