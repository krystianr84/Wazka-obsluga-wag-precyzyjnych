import re

from models.weight_reading import WeightReading, WeightStatus
from protocols.scale_protocol import ScaleProtocol

# Zdejmuje prefiks komendy z początku ramki masy, np.:
#   "SUI?  -   58.237 kg" → "?  -   58.237 kg"
#   "S     1832.0 g"      → "1832.0 g"   (spacja-stabilność zostaje ścięta przez .strip())
#   "DH   172.000 g"      → "172.000 g"
# Uwaga: SUI nie ma spacji między prefiksem a znakiem stabilności (pozycja 4 w ramce).
_CMD_PREFIX_RE = re.compile(
    r"^(?:SUI|SU|SI|S|DH|OT|UH|ODH|OUH)\s*",
    re.IGNORECASE,
)

# Ramka danych po usunięciu prefiksu i strip():
#   [stabilność][spacje][znak][spacje][cyfry][.,][cyfry][spacja][jednostka]
# Stabilność: ?, ^, v — spacja oznacza stabilną (po strip() jest usunięta)
# Znak:       -, + lub brak (spacja=dodatni, usunięta przez strip())
_VALUE_RE = re.compile(
    r"^([?^v])?"            # znacznik stabilności (opcjonalny)
    r"\s*([+-])?\s*"        # opcjonalny znak z otaczającymi spacjami
    r"([\d]+[.,][\d]+)"    # wartość z separatorem dziesiętnym
    r"\s+([a-zA-Z/]+)"     # jednostka
    r"\s*$",
    re.IGNORECASE,
)


class RadwagCbcp03Protocol(ScaleProtocol):
    """
    Radwag CBCP-03 — Character-based Communication Protocol v03.
    Stosowany w wagach serii WLY, C315, PUE 7.1 i innych.

    Komendy zakończone CR+LF, odpowiedzi zakończone CR+LF.

    Komendy:
        S    — wyślij wynik stabilny (w jednostce podstawowej)
        SI   — wyślij wynik stabilny (w bieżącej jednostce)  [basic unit]
        SU   — wyślij wynik stabilny (w bieżącej jednostce)  [current unit]
        SUI  — wyślij wynik natychmiastowy (w bieżącej jednostce)
        T    — tara
        Z    — zerowanie

    Format ramki masy wg specyfikacji CBCP-03 (pozycje):
        S: [S][ ][ ][stab][ ][znak][masa 9z][ ][jedn 3z]
        SUI: [S][U][I][stab][ ][znak][masa 9z][ ][jedn 3z]  ← brak spacji po SUI!
        Printout: [stab][ ][znak][masa 9z][ ][jedn 3z]

    Stabilność: ' '=stabilna, '?'=niestabilna, '^'=powyżej zakresu, 'v'=poniżej zakresu
    Znak:       ' '=dodatni, '-'=ujemny

    Odpowiedzi statusowe:
        XX A   — komenda przyjęta i w toku
        XX D   — komenda zakończona
        XX I   — komenda zrozumiana, nie może być wykonana
        XX OK  — komenda wykonana (np. DH OK, UH OK)
        XX E   — błąd timeout (oczekiwanie na stabilizację)
        XX ^   — przekroczenie zakresu (np. Z ^)
        XX v   — poniżej zakresu (np. T v)
        ES     — komenda niezrozumiana
        OL     — przekroczenie górnego zakresu wagi
        LO     — przekroczenie dolnego zakresu wagi
    """

    @property
    def name(self) -> str:
        return "Radwag CBCP-03"

    @property
    def weight_command(self) -> bytes:
        return b"S\r\n"

    @property
    def weight_immediate_command(self) -> bytes:
        return b"SUI\r\n"

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
            ("S",      "Odczyt stabilny (jedn. podstawowa)"),
            ("SI",     "Odczyt natychmiastowy (jedn. podstawowa)"),
            ("SU",     "Odczyt stabilny (bieżąca jedn.)"),
            ("SUI",    "Odczyt natychmiastowy (bieżąca jedn.)"),
            ("T",      "Tara"),
            ("OT",     "Odczyt wartości tary"),
            ("Z",      "Zerowanie"),
            ("C1",     "Transmisja ciągła — wł. (jedn. podst.)"),
            ("C0",     "Transmisja ciągła — wył. (jedn. podst.)"),
            ("CU1",    "Transmisja ciągła — wł. (bieżąca jedn.)"),
            ("CU0",    "Transmisja ciągła — wył. (bieżąca jedn.)"),
            ("DH",     "Ustaw próg dolny (np. DH 50.000)"),
            ("UH",     "Ustaw próg górny (np. UH 100.000)"),
            ("ODH",    "Odczyt progu dolnego"),
            ("OUH",    "Odczyt progu górnego"),
            ("NB",     "Numer seryjny wagi"),
            ("BP 350", "Sygnał dźwiękowy 350 ms"),
            ("PC",     "Lista wszystkich komend wagi"),
        ]

    def parse_response(self, line: str) -> WeightReading | None:
        line = line.strip()
        if not line:
            return None

        upper = line.upper()

        # Przekroczenie górnego zakresu wagi
        if upper.startswith("OL"):
            return WeightReading(value=0.0, unit="", status=WeightStatus.OVER_RANGE)

        # Przekroczenie dolnego zakresu wagi
        if upper.startswith("LO"):
            return WeightReading(value=0.0, unit="", status=WeightStatus.UNDER_RANGE)

        # Błąd: "ES" (komenda niezrozumiana), "ER..." lub "XX E" (timeout)
        if upper == "ES" or upper.startswith("ER"):
            return WeightReading(value=0.0, unit="", status=WeightStatus.ERROR)
        if re.match(r"^[A-Z0-9]+\s+E$", upper):
            return WeightReading(value=0.0, unit="", status=WeightStatus.ERROR)

        # Overflow komendy: "Z ^", "T ^" itp.
        if re.match(r"^[A-Z0-9]+\s+\^$", upper):
            return WeightReading(value=0.0, unit="", status=WeightStatus.OVER_RANGE)

        # Underflow komendy: "Z v", "T v" itp.
        if re.match(r"^[A-Z0-9]+\s+V$", upper):
            return WeightReading(value=0.0, unit="", status=WeightStatus.UNDER_RANGE)

        # Komenda zakończona sukcesem: "T D", "Z D", "S D", "K0 OK", "DH OK" itp.
        if re.match(r"^[A-Z0-9]+\s+(D|OK)$", upper):
            return WeightReading(value=0.0, unit="", status=WeightStatus.STABLE)

        # Komenda przyjęta / w toku: "S A", "T A", "SU A", "SUI A" itp.
        if re.match(r"^[A-Z0-9]+\s+A$", upper):
            return WeightReading(value=0.0, unit="", status=WeightStatus.IN_PROGRESS)

        # Komenda nie może być wykonana teraz: "S I", "SU I", "SUI I" itp.
        if re.match(r"^[A-Z0-9]+\s+I$", upper):
            return WeightReading(value=0.0, unit="", status=WeightStatus.IN_PROGRESS)

        # Ramka masy — zdejmij prefiks komendy i parsuj wartość
        data = _CMD_PREFIX_RE.sub("", line, count=1).strip()
        m = _VALUE_RE.match(data)
        if m:
            stability_char = (m.group(1) or "").lower()
            sign_str = m.group(2) or ""
            value_str = m.group(3).replace(",", ".")
            unit = m.group(4)

            try:
                value = float(value_str)
            except ValueError:
                return None

            if sign_str == "-":
                value = -value

            if stability_char == "?":
                status = WeightStatus.DYNAMIC
            elif stability_char == "^":
                status = WeightStatus.OVER_RANGE
            elif stability_char == "v":
                status = WeightStatus.UNDER_RANGE
            else:
                status = WeightStatus.STABLE

            return WeightReading(value=value, unit=unit, status=status)

        return None
