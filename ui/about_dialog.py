import os
import sys

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from ui.theme import ThemeManager


def _resource_path(relative: str) -> str:
    # sys._MEIPASS jest ustawiony przez PyInstaller w spakowanym pliku wykonywalnym
    base = getattr(sys, "_MEIPASS", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    return os.path.join(base, relative)


_IMG_DIR = _resource_path("img")


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("O programie")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setFixedSize(450, 450)

        t = ThemeManager.instance().theme

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(8)

        logo_label = QLabel()
        logo_path = os.path.join(_IMG_DIR, "festisite_nasa-2.PNG")
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = QLabel("Ważka")
        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        name.setFont(font)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        version = QLabel("Wersja 0.205.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet(f"color: {t.text_muted}; font-size: 11px;")

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {t.border_light};")

        desc = QLabel(
            "Aplikacja do komunikacji z wagami przemysłowymi\n"
            "i laboratoryjnymi przez interfejs RS-232.\n"
            "Copyright (c) 2026 Krystian Rutkowski\n"
            "Opublikowano na licencji: MIT License\n"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"color: {t.text};")

        protocols = QLabel(
            "Obsługiwane protokoły:\n"
            "Mettler Toledo (MT-SICS)  ·  Sartorius (SBI)\n"
            "Radwag (R)  ·  Radwag (CBCP-03)\n"
        )
        protocols.setAlignment(Qt.AlignmentFlag.AlignCenter)
        protocols.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(80)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        layout.addWidget(logo_label)
        layout.addSpacing(4)
        layout.addWidget(name)
        layout.addWidget(version)
        layout.addSpacing(4)
        layout.addWidget(line)
        layout.addSpacing(4)
        layout.addWidget(desc)
        layout.addWidget(protocols)
        layout.addStretch()
        layout.addLayout(btn_row)
