from models.weight_reading import WeightReading, WeightStatus
from protocols.scale_protocol import ScaleProtocol


class MettlerSicsProtocol(ScaleProtocol):
    """
    Protokół MT-SICS (Mettler Toledo Standard Interface Command Set) Level 0/1.
    Dokumentacja: MT-SICS Reference Manual, nr ref. 11780115.

    Komendy zakończone CR+LF, odpowiedzi zakończone CR+LF.
    Format odpowiedzi: <CMD> <STATUS> [<WARTOŚĆ> <JEDNOSTKA>]

    Przykłady:
        S S     50.000 g    — waga stabilna
        S D     50.000 g    — waga dynamiczna (niestabilna)
        T S      0.000 g    — tara wykonana
        Z A                 — zero potwierdzone
        S +                 — przekroczony zakres
        ES                  — błąd składni
    """

    @property
    def name(self) -> str:
        return "Mettler Toledo (MT-SICS)"

    @property
    def weight_command(self) -> bytes:
        return b"S\r\n"

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
            ("S",   "Odczyt stabilny (jedn. podstawowa)"),
            ("SI",  "Odczyt natychmiastowy (jedn. podstawowa)"),
            ("SU",  "Odczyt stabilny (bieżąca jedn.)"),
            ("SUI", "Odczyt natychmiastowy (bieżąca jedn.)"),
            ("T",   "Tara"),
            ("TI",  "Tara natychmiastowa"),
            ("Z",   "Zerowanie"),
            ("ZI",  "Zerowanie natychmiastowe"),
            ("@",   "Reset / inicjalizacja wagi"),
            ("I0",  "Obsługiwane poziomy MT-SICS"),
            ("I1",  "Zakres i rozdzielczość wagi"),
            ("I2",  "Wersja oprogramowania"),
            ("I3",  "Numer seryjny"),
            ("I4",  "Aktualna wartość tary"),
        ]

    def parse_response(self, line: str) -> WeightReading | None:
        line = line.strip()
        if not line:
            return None

        # Błędy składni: ES, ET, EZ
        if len(line) == 2 and line[0] == "E":
            return WeightReading(value=0.0, unit="", status=WeightStatus.ERROR)

        parts = line.split()
        if len(parts) < 2:
            return None

        cmd, status_code = parts[0], parts[1]

        if cmd == "Z":
            if status_code == "A":
                return WeightReading(value=0.0, unit="", status=WeightStatus.STABLE)
            if status_code == "I":
                return WeightReading(value=0.0, unit="", status=WeightStatus.IN_PROGRESS)
            return self._range_error(status_code)

        if cmd in ("S", "T"):
            if status_code in ("+", "-"):
                return self._range_error(status_code)
            if status_code == "I" and len(parts) < 3:
                # "T I" bez wartości = tara w trakcie
                return WeightReading(value=0.0, unit="", status=WeightStatus.IN_PROGRESS)
            if len(parts) >= 3:
                try:
                    value = float(parts[2].replace(",", "."))
                except ValueError:
                    return None
                unit = parts[3] if len(parts) >= 4 else ""
                status = self._map_status(status_code)
                return WeightReading(value=value, unit=unit, status=status)

        return None

    @staticmethod
    def _map_status(code: str) -> WeightStatus:
        # Nieznany kod statusu przy obecnej wartości traktujemy jako stabilną,
        # żeby nie gubić odczytu 0.000 przy niestandardowych kodach wagi.
        return {
            "S": WeightStatus.STABLE,
            "D": WeightStatus.DYNAMIC,
            "I": WeightStatus.STABLE,
        }.get(code, WeightStatus.STABLE)

    @staticmethod
    def _range_error(code: str) -> WeightReading:
        status = WeightStatus.OVER_RANGE if code == "+" else WeightStatus.UNDER_RANGE
        return WeightReading(value=0.0, unit="", status=status)
