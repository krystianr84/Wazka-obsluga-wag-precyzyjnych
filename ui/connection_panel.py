from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtSerialPort import QSerialPort

from models.scale_preset import ScalePreset
from services.scale_service import (
    AVAILABLE_PROTOCOLS, AVAILABLE_BAUD_RATES,
    PARITY_OPTIONS, DATA_BITS_OPTIONS, STOP_BITS_OPTIONS,
    ScaleService,
)
from services.preset_service import PresetService
from ui.theme import ThemeManager


class ConnectionPanel(QGroupBox):
    # port, baud, parity, data_bits, stop_bits
    connect_requested = pyqtSignal(str, int, object, object, object)
    disconnect_requested = pyqtSignal()

    def __init__(self, service: ScaleService, preset_service: PresetService, parent=None):
        super().__init__("Połączenie", parent)
        self._service = service
        self._preset_service = preset_service

        root = QVBoxLayout(self)
        root.setSpacing(8)

        # ── Rząd 0: zarządzanie profilami ─────────────────────────────────
        row0 = QHBoxLayout()
        row0.setSpacing(8)

        self._preset_label = QLabel("Profil:")

        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(180)

        self._load_btn = QPushButton("Wczytaj")
        self._load_btn.setFixedHeight(28)
        self._load_btn.setToolTip("Wczytaj ustawienia z wybranego profilu do formularza")
        self._load_btn.clicked.connect(self._on_load_preset)

        self._save_btn = QPushButton("Zapisz profil…")
        self._save_btn.setFixedHeight(28)
        self._save_btn.setToolTip("Zapisz bieżące ustawienia jako nowy profil")
        self._save_btn.clicked.connect(self._on_save_preset)

        self._delete_btn = QPushButton("Usuń")
        self._delete_btn.setFixedHeight(28)
        self._delete_btn.setToolTip("Usuń wybrany profil")
        self._delete_btn.clicked.connect(self._on_delete_preset)

        row0.addWidget(self._preset_label)
        row0.addWidget(self._preset_combo, stretch=1)
        row0.addWidget(self._load_btn)
        row0.addWidget(self._save_btn)
        row0.addWidget(self._delete_btn)
        row0.addStretch()

        # ── Rząd 1: protokół, port, odśwież, baud rate, przycisk ──────────
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        self._protocol_combo = _LabeledCombo("Protokół", [p.name for p in AVAILABLE_PROTOCOLS])
        self._protocol_combo.combo.currentIndexChanged.connect(self._on_protocol_changed)

        self._port_combo = _LabeledCombo("Port szeregowy", [])
        self._refresh_ports()

        self._refresh_btn = QPushButton("↻")
        self._refresh_btn.setFixedSize(36, 36)
        self._refresh_btn.setToolTip("Odśwież listę portów")
        self._refresh_btn.clicked.connect(self._refresh_ports)
        refresh_wrap = QVBoxLayout()
        refresh_wrap.setSpacing(2)
        refresh_wrap.addWidget(QLabel(""))
        refresh_wrap.addWidget(self._refresh_btn)

        self._baud_combo = _LabeledCombo("Baud rate", [str(b) for b in AVAILABLE_BAUD_RATES])
        self._baud_combo.combo.setCurrentText(str(service.protocol.default_baud_rate))

        self._connect_btn = QPushButton("Połącz")
        self._connect_btn.setFixedWidth(100)
        self._connect_btn.setFixedHeight(36)
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        connect_wrap = QVBoxLayout()
        connect_wrap.setSpacing(2)
        connect_wrap.addWidget(QLabel(""))
        connect_wrap.addWidget(self._connect_btn)

        row1.addWidget(self._protocol_combo, stretch=3)
        row1.addWidget(self._port_combo, stretch=2)
        row1.addLayout(refresh_wrap)
        row1.addWidget(self._baud_combo, stretch=2)
        row1.addLayout(connect_wrap)

        # ── Rząd 2: długość słowa, parzystość, bity stopu ─────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        self._data_bits_combo = _LabeledCombo("Długość słowa (bity danych)", list(DATA_BITS_OPTIONS))
        self._data_bits_combo.combo.setCurrentText("8")

        self._parity_combo = _LabeledCombo("Parzystość", list(PARITY_OPTIONS))
        self._parity_combo.combo.setCurrentText("Brak (N)")

        self._stop_bits_combo = _LabeledCombo("Bity stopu", list(STOP_BITS_OPTIONS))
        self._stop_bits_combo.combo.setCurrentText("1")

        row2.addWidget(self._data_bits_combo, stretch=1)
        row2.addWidget(self._parity_combo, stretch=1)
        row2.addWidget(self._stop_bits_combo, stretch=1)
        row2.addStretch(2)

        root.addLayout(row0)
        root.addLayout(row1)
        root.addLayout(row2)

        self._refresh_presets()
        self._is_connected = False

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    # ── Publiczne ──────────────────────────────────────────────────────────

    def set_connected(self, connected: bool):
        self._is_connected = connected
        form_widgets = [
            self._protocol_combo.combo,
            self._port_combo.combo,
            self._baud_combo.combo,
            self._data_bits_combo.combo,
            self._parity_combo.combo,
            self._stop_bits_combo.combo,
            self._refresh_btn,
            self._load_btn,
        ]
        for w in form_widgets:
            w.setEnabled(not connected)

        t = ThemeManager.instance().theme
        if connected:
            self._connect_btn.setText("Rozłącz")
            self._connect_btn.setStyleSheet(
                f"QPushButton {{ background-color: {t.btn_disconnect}; color: white; border-radius: 4px; }}"
                f"QPushButton:hover {{ background-color: {t.btn_disconnect_hover}; }}"
            )
        else:
            self._connect_btn.setText("Połącz")
            self._connect_btn.setStyleSheet(
                f"QPushButton {{ background-color: {t.btn_connect}; color: white; border-radius: 4px; }}"
                f"QPushButton:hover {{ background-color: {t.btn_connect_hover}; }}"
                f"QPushButton:disabled {{ background-color: {t.btn_disabled_bg}; }}"
            )

    # ── Prywatne — motyw ──────────────────────────────────────────────────

    def _apply_theme(self):
        t = ThemeManager.instance().theme
        self._preset_label.setStyleSheet(f"font-size: 11px; color: {t.text_secondary};")
        self._delete_btn.setStyleSheet(
            f"QPushButton {{ color: {t.delete_fg}; }}"
            f"QPushButton:hover {{ color: {t.delete_hover}; }}"
            f"QPushButton:disabled {{ color: {t.text_disabled}; }}"
        )
        for combo_widget in (
            self._protocol_combo, self._port_combo, self._baud_combo,
            self._data_bits_combo, self._parity_combo, self._stop_bits_combo,
        ):
            combo_widget.apply_theme()
        # Re-apply connect button style to reflect current state
        self.set_connected(self._is_connected)

    # ── Prywatne — połączenie ──────────────────────────────────────────────

    def _on_connect_clicked(self):
        if self._service.is_connected:
            self.disconnect_requested.emit()
            return
        port = self._port_combo.combo.currentText()
        baud = int(self._baud_combo.combo.currentText())
        parity = PARITY_OPTIONS[self._parity_combo.combo.currentText()]
        data_bits = DATA_BITS_OPTIONS[self._data_bits_combo.combo.currentText()]
        stop_bits = STOP_BITS_OPTIONS[self._stop_bits_combo.combo.currentText()]
        self.connect_requested.emit(port, baud, parity, data_bits, stop_bits)

    def _on_protocol_changed(self, index: int):
        protocol = AVAILABLE_PROTOCOLS[index]
        self._service.set_protocol(protocol)
        self._baud_combo.combo.setCurrentText(str(protocol.default_baud_rate))

    def _refresh_ports(self):
        current = self._port_combo.combo.currentText()
        self._port_combo.combo.clear()
        ports = self._service.available_ports()
        self._port_combo.combo.addItems(ports)
        if current in ports:
            self._port_combo.combo.setCurrentText(current)

    # ── Prywatne — profile ─────────────────────────────────────────────────

    def _refresh_presets(self):
        presets = self._preset_service.presets
        self._preset_combo.clear()
        if presets:
            self._preset_combo.addItems([p.name for p in presets])
        else:
            self._preset_combo.addItem("Brak zapisanych profili")
        has = bool(presets)
        self._preset_combo.setEnabled(has)
        self._load_btn.setEnabled(has)
        self._delete_btn.setEnabled(has)

    def _on_load_preset(self):
        name = self._preset_combo.currentText()
        preset = next((p for p in self._preset_service.presets if p.name == name), None)
        if preset is None:
            return
        self._apply_preset_to_form(preset)

    def _apply_preset_to_form(self, preset: ScalePreset):
        proto_idx = next(
            (i for i, p in enumerate(AVAILABLE_PROTOCOLS) if p.name == preset.protocol_name), 0
        )
        self._protocol_combo.combo.setCurrentIndex(proto_idx)

        ports = self._service.available_ports()
        if preset.port not in ports:
            self._port_combo.combo.addItem(preset.port)
        self._port_combo.combo.setCurrentText(preset.port)

        self._baud_combo.combo.setCurrentText(str(preset.baud_rate))
        self._parity_combo.combo.setCurrentText(preset.parity)
        self._data_bits_combo.combo.setCurrentText(preset.data_bits)
        self._stop_bits_combo.combo.setCurrentText(preset.stop_bits)

    def _on_save_preset(self):
        suggested = self._preset_combo.currentText()
        if suggested == "Brak zapisanych profili":
            suggested = ""
        name, ok = QInputDialog.getText(
            self, "Zapisz profil", "Nazwa profilu:", text=suggested
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        preset = ScalePreset(
            name=name,
            protocol_name=AVAILABLE_PROTOCOLS[self._protocol_combo.combo.currentIndex()].name,
            port=self._port_combo.combo.currentText(),
            baud_rate=int(self._baud_combo.combo.currentText()),
            parity=self._parity_combo.combo.currentText(),
            data_bits=self._data_bits_combo.combo.currentText(),
            stop_bits=self._stop_bits_combo.combo.currentText(),
        )
        self._preset_service.save_preset(preset)
        self._refresh_presets()
        self._preset_combo.setCurrentText(name)

    def _on_delete_preset(self):
        name = self._preset_combo.currentText()
        reply = QMessageBox.question(
            self, "Usuń profil",
            f'Czy na pewno usunąć profil "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._preset_service.delete_preset(name)
        self._refresh_presets()


# ── Pomocnicze ────────────────────────────────────────────────────────────

class _LabeledCombo(QWidget):
    def __init__(self, label: str, items: list[str], parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self._lbl = QLabel(label)
        self.combo = QComboBox()
        self.combo.addItems(items)
        layout.addWidget(self._lbl)
        layout.addWidget(self.combo)
        self.apply_theme()

    def apply_theme(self):
        t = ThemeManager.instance().theme
        self._lbl.setStyleSheet(f"font-size: 11px; color: {t.text_secondary};")
