from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QGroupBox, QRadioButton, QButtonGroup, QComboBox, QLabel,
)
from PyQt6.QtCore import Qt

from services.app_settings_service import AppSettingsService, AVAILABLE_INTERVALS
from services.scale_service import ScaleService
from ui.theme import ThemeManager


class AppSettingsDialog(QDialog):
    def __init__(self, settings_service: AppSettingsService, scale_service: ScaleService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opcje aplikacji")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setFixedWidth(320)
        self.setModal(True)

        self._settings_service = settings_service
        self._scale_service = scale_service

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 12)

        # ── Motyw ─────────────────────────────────────────────────────────
        theme_group = QGroupBox("Motyw")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(6)

        self._btn_group = QButtonGroup(self)
        self._radio_dark = QRadioButton("Ciemny (domyślny)")
        self._radio_light = QRadioButton("Jasny")
        self._btn_group.addButton(self._radio_dark)
        self._btn_group.addButton(self._radio_light)

        if ThemeManager.instance().theme.name == "light":
            self._radio_light.setChecked(True)
        else:
            self._radio_dark.setChecked(True)

        theme_layout.addWidget(self._radio_dark)
        theme_layout.addWidget(self._radio_light)
        layout.addWidget(theme_group)

        # ── Interwał odczytu ciągłego ──────────────────────────────────────
        interval_group = QGroupBox("Interwał odczytu ciągłego")
        interval_layout = QVBoxLayout(interval_group)
        interval_layout.setSpacing(6)

        self._interval_combo = QComboBox()
        current_ms = settings_service.interval_ms
        selected_index = 0
        for i, (ms, label) in enumerate(AVAILABLE_INTERVALS):
            self._interval_combo.addItem(label, userData=ms)
            if ms == current_ms:
                selected_index = i
        self._interval_combo.setCurrentIndex(selected_index)

        interval_layout.addWidget(self._interval_combo)
        layout.addWidget(interval_group)

        # ── Przyciski OK / Anuluj ──────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(80)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.setFixedWidth(80)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _on_ok(self):
        theme_name = "light" if self._radio_light.isChecked() else "dark"
        self._settings_service.set_theme(theme_name)
        ThemeManager.instance().set_theme(theme_name)

        ms = self._interval_combo.currentData()
        self._settings_service.set_interval_ms(ms)
        self._scale_service.set_continuous_interval(ms)

        self.accept()
