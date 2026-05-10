import re

from models.weight_reading import WeightReading, WeightStatus
from protocols.scale_protocol import ScaleProtocol

# Dopasowuje obie odmiany formatu Radwag:
#   "ST,GS,+   50.000000 g"   — pola rozdzielone przecinkami
#   "ST +      50.000000 g"   — pola rozdzielone spacjami
_WEIGHT_RE = re.compile(
    r"\b(ST|US|OI)\b"           # kod stabilności
    r".*?"                       # opcjonalne pole GS/NT i przecinki
    r"([+-])"                    # znak
    r"\s*([\d]+[.,][\d]+)"      # wartość z separatorem dziesiętnym
    r"\s+([a-zA-Z/]+)",         # jednostka (g, kg, lb, N, itp.)
    re.IGNORECASE,
)

_STATUS_MAP = {
    "ST": WeightStatus.STABLE,
    "US": WeightStatus.DYNAMIC,
    "OI": WeightStatus.IN_PROGRESS,
}


class RadwagProtocol(ScaleProtocol):
    """
    Protokół Radwag "R" — standard dla wag serii WLY, WPS, AS, PS i innych.
    Przetestowany na modelu WLY 6/F1/K (RS-232, 9600 baud, 8N1).
    sics
    Komendy zakończone CR+LF, odpowiedzi zakończone CR+LF.

    Format odpowiedzi (dwie obsługiwane odmiany):
        ST,GS,+   50.000000 g    — stabilna, brutto
        ST,NT,-    0.000000 g    — stabilna, netto (po tarze)
        US,GS,+   50.000000 g    — niestabilna
        OL                       — przekroczony zakres
        A                        — komenda przyjęta (tara/zero)
        E                        — błąd

    Komendy:
        SU  — odczyt wagi stabilnej w bieżącej jednostce
        SI  — odczyt wagi natychmiastowej
        T   — tara
        Z   — zerowanie
    """

    @property
    def name(self) -> str:
        return "Radwag (WLY / R protocol)"

    @property
    def weight_command(self) -> bytes:
        return b"SU\r\n"

    @property
    def weight_immediate_command(self) -> bytes:
        return b"SI\r\n"

    @property
    def tare_command(self) -> bytes:
        return b"T\r\n"

    @property
    def zero_command(self) -> bytes:
        return b"Z\r\n"

    @property
    def default_baud_rate(self) -> int:
        return 9600

    @property
    def command_list(self) -> list[tuple[str, str]]:
        return [
            ("SU",  "Odczyt stabilny (bieżąca jedn.)"),
            ("SI",  "Odczyt natychmiastowy"),
            ("T",   "Tara"),
            ("OT",  "Odczyt wartości tary"),
            ("Z",   "Zerowanie"),
            ("NB",  "Numer seryjny wagi"),
        ]

    def parse_response(self, line: str) -> WeightReading | None:
        line = line.strip()
        if not line:
            return None

        upper = line.upper()

        # Przekroczenie zakresu
        if upper.startswith("OL"):
            return WeightReading(value=0.0, unit="", status=WeightStatus.OVER_RANGE)

        # Błąd
        if upper == "E" or upper.startswith("ES") or upper.startswith("ERR"):
            return WeightReading(value=0.0, unit="", status=WeightStatus.ERROR)

        # Potwierdzenie komendy (tara/zero): "A" lub "T A" lub "Z A"
        if upper in ("A", "T A", "Z A"):
            return WeightReading(value=0.0, unit="", status=WeightStatus.STABLE)

        # Główny format z wartością wagową
        m = _WEIGHT_RE.search(line)
        if m:
            stability_code = m.group(1).upper()
            sign = -1.0 if m.group(2) == "-" else 1.0
            value_str = m.group(3).replace(",", ".")
            unit = m.group(4)

            try:
                value = sign * float(value_str)
            except ValueError:
                return None

            status = _STATUS_MAP.get(stability_code, WeightStatus.STABLE)
            return WeightReading(value=value, unit=unit, status=status)

        return None
