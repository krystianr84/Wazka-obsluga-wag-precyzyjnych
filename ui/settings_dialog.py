from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt

from services.scale_service import ScaleService
from services.preset_service import PresetService
from ui.connection_panel import ConnectionPanel


class SettingsDialog(QDialog):
    def __init__(self, service: ScaleService, preset_service: PresetService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia połączenia")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(740)
        self.setModal(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        self._panel = ConnectionPanel(service, preset_service)
        self._panel.connect_requested.connect(service.connect)
        self._panel.disconnect_requested.connect(service.disconnect)
        service.connection_changed.connect(self._panel.set_connected)
        self._panel.set_connected(service.is_connected)

        layout.addWidget(self._panel)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Zamknij")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
