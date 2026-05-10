from dataclasses import dataclass


@dataclass
class ScalePreset:
    name: str
    protocol_name: str
    port: str
    baud_rate: int
    parity: str     # klucz z PARITY_OPTIONS
    data_bits: str  # klucz z DATA_BITS_OPTIONS
    stop_bits: str  # klucz z STOP_BITS_OPTIONS
