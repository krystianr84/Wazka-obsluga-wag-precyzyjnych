from models.weight_reading import WeightReading, WeightStatus
from protocols.scale_protocol import ScaleProtocol


class SartoriusSbiProtocol(ScaleProtocol):
    """
    Protokół Sartorius SBI (Sartorius Balance Interface).
    Obsługiwane modele: Entris, Quintix, Cubis, Practum, Secura i inne z RS-232.

    Komendy zakończone CR+LF.
    Format odpowiedzi: <ZNAK_STATUSU><WARTOŚĆ><SPACJA><JEDNOSTKA>

    Znaki statusu:
        '+'  — waga stabilna, wartość dodatnia
        '-'  — waga stabilna, wartość ujemna
        'S'  — waga niestabilna (swinging/dynamiczna)
        'I'  — waga zajęta (in progress)
        'O'  — przekroczony zakres (overload)
        'E'  — błąd

    Przykłady:
        "+  50.000 g"   — stabilna, 50 g
        "-   0.010 g"   — stabilna, -0.010 g
        "S  50.000 g"   — niestabilna, 50 g
        "I"             — w trakcie stabilizacji
        "O"             — przekroczony zakres
    """

    @property
    def name(self) -> str:
        return "Sartorius (SBI)"

    @property
    def weight_command(self) -> bytes:
        return b"P\r\n"

    @property
    def weight_immediate_command(self) -> bytes:
        return b"P\r\n"

    @property
    def tare_command(self) -> bytes:
        return b"T\r\n"

    @property
    def zero_command(self) -> bytes:
        return b"Z\r\n"

    @property
    def default_baud_rate(self) -> int:
        return 1200

    @property
    def command_list(self) -> list[tuple[str, str]]:
        return [
            ("P",  "Odczyt wagi (Print)"),
            ("T",  "Tara"),
            ("Z",  "Zerowanie"),
            ("C",  "Stałe wysyłanie wyników (Continuous)"),
            ("K",  "Zatrzymanie transmisji ciągłej"),
        ]

    def parse_response(self, line: str) -> WeightReading | None:
        line = line.strip()
        if not line:
            return None

        first = line[0]

        if first == "I":
            return WeightReading(value=0.0, unit="", status=WeightStatus.IN_PROGRESS)

        if first == "O":
            return WeightReading(value=0.0, unit="", status=WeightStatus.OVER_RANGE)

        if first == "E":
            return WeightReading(value=0.0, unit="", status=WeightStatus.ERROR)

        if first not in ("+", "-", "S"):
            return None

        rest = line[1:].strip()

        space_idx = rest.rfind(" ")
        if space_idx < 1:
            # Brak jednostki — cały ciąg to wartość (np. "+0.000")
            value_str = rest
            unit = ""
        else:
            value_str = rest[:space_idx].strip()
            unit = rest[space_idx + 1:].strip()

        try:
            value = float(value_str.replace(",", "."))
        except ValueError:
            return None

        if first == "-":
            value = -value

        status = WeightStatus.DYNAMIC if first == "S" else WeightStatus.STABLE
        return WeightReading(value=value, unit=unit, status=status)
