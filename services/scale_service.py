import re
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo

from models.weight_reading import WeightReading, WeightStatus
from protocols.scale_protocol import ScaleProtocol
from protocols.mettler_sics_protocol import MettlerSicsProtocol
from protocols.sartorius_sbi_protocol import SartoriusSbiProtocol
from protocols.radwag_protocol import RadwagProtocol
from protocols.radwag_cbcp03_protocol import RadwagCbcp03Protocol

AVAILABLE_PROTOCOLS: list[ScaleProtocol] = [
    MettlerSicsProtocol(),
    SartoriusSbiProtocol(),
    RadwagProtocol(),
    RadwagCbcp03Protocol(),
]

AVAILABLE_BAUD_RATES = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]

PARITY_OPTIONS: dict[str, QSerialPort.Parity] = {
    "Brak (N)":        QSerialPort.Parity.NoParity,
    "Parzysta (E)":    QSerialPort.Parity.EvenParity,
    "Nieparzysta (O)": QSerialPort.Parity.OddParity,
    "Space (S)":       QSerialPort.Parity.SpaceParity,
    "Mark (M)":        QSerialPort.Parity.MarkParity,
}

DATA_BITS_OPTIONS: dict[str, QSerialPort.DataBits] = {
    "5": QSerialPort.DataBits.Data5,
    "6": QSerialPort.DataBits.Data6,
    "7": QSerialPort.DataBits.Data7,
    "8": QSerialPort.DataBits.Data8,
}

STOP_BITS_OPTIONS: dict[str, QSerialPort.StopBits] = {
    "1":   QSerialPort.StopBits.OneStop,
    "1.5": QSerialPort.StopBits.OneAndHalfStop,
    "2":   QSerialPort.StopBits.TwoStop,
}

# Skróty do notacji XnS (np. 8N1, 8E2)
_PARITY_LETTER: dict[QSerialPort.Parity, str] = {
    QSerialPort.Parity.NoParity:    "N",
    QSerialPort.Parity.EvenParity:  "E",
    QSerialPort.Parity.OddParity:   "O",
    QSerialPort.Parity.SpaceParity: "S",
    QSerialPort.Parity.MarkParity:  "M",
}

_STOP_BITS_LABEL: dict[QSerialPort.StopBits, str] = {
    QSerialPort.StopBits.OneStop:         "1",
    QSerialPort.StopBits.OneAndHalfStop:  "1.5",
    QSerialPort.StopBits.TwoStop:         "2",
}

MAX_LOG_ENTRIES = 200


_STATS_STATUSES = {WeightStatus.STABLE, WeightStatus.DYNAMIC}


class ScaleService(QObject):
    reading_updated = pyqtSignal(object)        # WeightReading
    log_added = pyqtSignal(str)
    connection_changed = pyqtSignal(bool)       # True = połączono
    error_occurred = pyqtSignal(str)
    continuous_changed = pyqtSignal(bool)       # True = odczyt ciągły aktywny
    protocol_changed = pyqtSignal(object)       # ScaleProtocol
    # min, max, mean, stddev, unit
    session_stats_updated = pyqtSignal(float, float, float, float, str)
    session_stats_reset = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._protocol: ScaleProtocol = AVAILABLE_PROTOCOLS[0]
        self._port = QSerialPort(self)
        self._port.readyRead.connect(self._on_ready_read)
        self._port.errorOccurred.connect(self._on_port_error)
        self._buffer = ""
        self._log: list[str] = []
        self._connection_info: str = ""
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_timer_tick)
        self._session_min: float | None = None
        self._session_max: float | None = None
        self._session_unit: str = ""
        self._session_count: int = 0
        self._session_mean: float = 0.0
        self._session_M2: float = 0.0   # Welford's running sum of squared deviations

    @property
    def connection_info(self) -> str:
        return self._connection_info

    @staticmethod
    def available_ports() -> list[str]:
        return [p.portName() for p in QSerialPortInfo.availablePorts()]

    @property
    def protocol(self) -> ScaleProtocol:
        return self._protocol

    @property
    def is_connected(self) -> bool:
        return self._port.isOpen()

    def set_protocol(self, protocol: ScaleProtocol):
        self._protocol = protocol
        self.protocol_changed.emit(protocol)

    @property
    def is_continuous(self) -> bool:
        return self._timer.isActive()

    def set_continuous_interval(self, ms: int) -> None:
        self._timer.setInterval(ms)
        if self._timer.isActive():
            self._timer.stop()
            self._timer.start()

    def start_continuous(self):
        if not self._port.isOpen():
            return
        ms = self._timer.interval()
        label = f"{ms // 1000} s" if ms >= 1000 and ms % 1000 == 0 else f"{ms} ms"
        self._add_log(f"Odczyt ciągły: START ({label})")
        self._timer.start()
        self.continuous_changed.emit(True)

    def stop_continuous(self):
        if self._timer.isActive():
            self._timer.stop()
            self._add_log("Odczyt ciągły: STOP")
            self.continuous_changed.emit(False)

    def _on_timer_tick(self):
        if not self._port.isOpen():
            self.stop_continuous()
            return
        self._port.write(self._protocol.weight_immediate_command)

    def connect(
        self,
        port_name: str,
        baud_rate: int,
        parity: QSerialPort.Parity = QSerialPort.Parity.NoParity,
        data_bits: QSerialPort.DataBits = QSerialPort.DataBits.Data8,
        stop_bits: QSerialPort.StopBits = QSerialPort.StopBits.OneStop,
    ):
        if self._port.isOpen():
            self._port.close()

        self._port.setPortName(port_name)
        self._port.setBaudRate(baud_rate)
        self._port.setDataBits(data_bits)
        self._port.setParity(parity)
        self._port.setStopBits(stop_bits)
        self._port.setFlowControl(QSerialPort.FlowControl.NoFlowControl)

        if self._port.open(QSerialPort.OpenModeFlag.ReadWrite):
            self._buffer = ""
            bits = data_bits.value if hasattr(data_bits, "value") else int(data_bits)
            parity_letter = _PARITY_LETTER.get(parity, "?")
            stop_label = _STOP_BITS_LABEL.get(stop_bits, "?")
            self._connection_info = (
                f"{port_name}  @  {baud_rate} baud  |  "
                f"{bits}{parity_letter}{stop_label}  [{self._protocol.name}]"
            )
            self._add_log(f"Połączono z {self._connection_info}")
            self.connection_changed.emit(True)
        else:
            msg = f"Nie można otworzyć portu {port_name}: {self._port.errorString()}"
            self._add_log(f"BŁĄD: {msg}")
            self.error_occurred.emit(msg)

    def disconnect(self):
        self.stop_continuous()
        if self._port.isOpen():
            self._port.close()
        self._buffer = ""
        self._connection_info = ""
        self._reset_session_stats()
        self._add_log("Rozłączono.")
        self.connection_changed.emit(False)

    def send_raw(self, text: str):
        if not self._port.isOpen():
            return
        command = text.strip()
        if not command:
            return
        self._port.write((command + "\r\n").encode(errors="replace"))
        self._add_log(f">> {command}")

    def request_weight(self):
        self._send(self._protocol.weight_command, "Zapytanie o wagę")

    def request_weight_immediate(self):
        self._send(self._protocol.weight_immediate_command, "Zapytanie natychmiastowe")

    def tare(self):
        self._reset_session_stats()
        self._send(self._protocol.tare_command, "Tara")

    def zero(self):
        self._reset_session_stats()
        self._send(self._protocol.zero_command, "Zerowanie")

    def _reset_session_stats(self):
        self._session_min = None
        self._session_max = None
        self._session_unit = ""
        self._session_count = 0
        self._session_mean = 0.0
        self._session_M2 = 0.0
        self.session_stats_reset.emit()

    def _update_session_stats(self, reading: WeightReading):
        if reading.status not in _STATS_STATUSES:
            return
        v = reading.value
        if self._session_min is None or v < self._session_min:
            self._session_min = v
        if self._session_max is None or v > self._session_max:
            self._session_max = v
        self._session_unit = reading.unit

        # Algorytm Welforda — populacyjne odchylenie standardowe
        self._session_count += 1
        delta = v - self._session_mean
        self._session_mean += delta / self._session_count
        self._session_M2 += delta * (v - self._session_mean)
        stddev = (self._session_M2 / self._session_count) ** 0.5

        self.session_stats_updated.emit(
            self._session_min, self._session_max,
            self._session_mean, stddev,
            self._session_unit,
        )

    def _send(self, command: bytes, label: str):
        if not self._port.isOpen():
            return
        self._port.write(command)
        self._add_log(f">> {label} ({command.strip().decode()})")

    def _on_ready_read(self):
        data = bytes(self._port.readAll())
        # Normalizuj wszystkie warianty zakończenia linii do \n
        chunk = data.decode(errors="replace").replace("\r\n", "\n").replace("\r", "\n")
        self._buffer += chunk

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.replace("\x00", "").strip()
            if len(line) == 0:
                continue
            self._add_log(f"<< {line}")
            reading = self._protocol.parse_response(line)
            if reading is None:
                reading = _fallback_parse(line)
            if reading is not None:
                self.reading_updated.emit(reading)
                self._update_session_stats(reading)
            elif not self._timer.isActive():
                self._add_log(f"?? nierozpoznana odpowiedź: {repr(line)}")

    def _on_port_error(self, error):
        if error == QSerialPort.SerialPortError.NoError:
            return
        msg = self._port.errorString()
        self._add_log(f"BŁĄD portu: {msg}")
        self.error_occurred.emit(msg)
        if self._port.isOpen():
            self._port.close()
            self.connection_changed.emit(False)

    def _add_log(self, entry: str):
        ts = datetime.now().strftime("%H:%M:%S")
        full = f"[{ts}] {entry}"
        self._log.append(full)
        if len(self._log) > MAX_LOG_ENTRIES:
            self._log.pop(0)
        self.log_added.emit(full)


# ---------------------------------------------------------------------------
# Format awaryjny: wartość bez prefiksu komendy, np. "0,000g" lub "50.000 g"
# Obsługuje: opcjonalny znak, przecinek lub kropkę, jednostkę bez spacji
# ---------------------------------------------------------------------------
_COMPACT_RE = re.compile(
    r"^([+-]?)\s*([\d]+[.,][\d]+)\s*([a-zA-Z/]+)$"
)


def _fallback_parse(line: str) -> "WeightReading | None":
    m = _COMPACT_RE.match(line.strip())
    if not m:
        return None
    sign_str, value_str, unit = m.group(1), m.group(2), m.group(3)
    try:
        value = float(value_str.replace(",", "."))
    except ValueError:
        return None
    if sign_str == "-":
        value = -value
    return WeightReading(value=value, unit=unit, status=WeightStatus.STABLE)
