import html as _html

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QPlainTextEdit, QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem, QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.theme import ThemeManager


class TerminalDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Terminal komunikacji")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setModal(False)
        self.resize(880, 500)

        self._service = service
        service.log_added.connect(self._on_log)
        service.connection_changed.connect(self._on_connection_changed)
        service.protocol_changed.connect(self._on_protocol_changed)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont("Courier New", 9))
        self._log_view.setMaximumBlockCount(500)
        splitter.addWidget(self._log_view)

        legend_widget = self._build_legend()
        splitter.addWidget(legend_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([580, 260])
        root.addWidget(splitter, stretch=1)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        lbl = QLabel("Komenda:")
        lbl.setFixedWidth(70)

        self._input = QLineEdit()
        self._input.setPlaceholderText("np. S, SI, T, Z  —  CR LF dodawane automatycznie")
        self._input.setFont(QFont("Courier New", 10))
        self._input.returnPressed.connect(self._send)

        self._send_btn = QPushButton("Wyślij")
        self._send_btn.setFixedWidth(80)
        self._send_btn.setDefault(True)
        self._send_btn.clicked.connect(self._send)

        self._clear_btn = QPushButton("Wyczyść")
        self._clear_btn.setFixedWidth(80)
        self._clear_btn.clicked.connect(self._log_view.clear)

        input_row.addWidget(lbl)
        input_row.addWidget(self._input, stretch=1)
        input_row.addWidget(self._send_btn)
        input_row.addWidget(self._clear_btn)
        root.addLayout(input_row)

        self._on_connection_changed(service.is_connected)
        self._rebuild_commands(service.protocol)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    # ── Budowanie legendy ─────────────────────────────────────────────────

    def _build_legend(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(4)

        self._legend_header = QLabel("Dostępne komendy")
        self._legend_header.setStyleSheet("font-size: 11px; font-weight: bold;")

        self._legend_hint = QLabel("Dwuklik → wstaw do pola")
        self._legend_hint.setStyleSheet("font-size: 10px;")

        self._cmd_list = QListWidget()
        self._cmd_list.setFont(QFont("Courier New", 9))
        self._cmd_list.itemDoubleClicked.connect(self._on_command_double_clicked)

        layout.addWidget(self._legend_header)
        layout.addWidget(self._legend_hint)
        layout.addWidget(self._cmd_list, stretch=1)
        return container

    # ── Motyw ─────────────────────────────────────────────────────────────

    def _apply_theme(self):
        t = ThemeManager.instance().theme
        self._log_view.setStyleSheet(
            f"background-color: {t.bg_panel}; color: {t.text}; border-radius: 4px;"
        )
        self._legend_header.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {t.text_secondary};"
        )
        self._legend_hint.setStyleSheet(f"font-size: 10px; color: {t.text_dim};")
        self._cmd_list.setStyleSheet(
            f"QListWidget {{"
            f"  background-color: {t.bg_list}; color: {t.text};"
            f"  border: 1px solid {t.border}; border-radius: 4px;"
            f"}}"
            f"QListWidget::item {{ padding: 3px 6px; }}"
            f"QListWidget::item:hover {{ background-color: {t.bg_input}; }}"
            f"QListWidget::item:selected {{ background-color: {t.btn_weight}; color: white; }}"
        )
        self._send_btn.setStyleSheet(
            f"QPushButton {{ background-color: {t.btn_weight}; color: white; border-radius: 4px; }}"
            f"QPushButton:hover {{ background-color: {t.btn_weight_now}; }}"
            f"QPushButton:disabled {{ background-color: {t.btn_disabled_bg}; color: {t.btn_disabled_fg}; }}"
        )
        self._clear_btn.setStyleSheet(
            f"QPushButton {{ background-color: {t.bg_input}; color: {t.text}; border-radius: 4px; }}"
            f"QPushButton:hover {{ background-color: {t.bg_input_hover}; }}"
        )

    # ── Sloty ─────────────────────────────────────────────────────────────

    def _send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._service.send_raw(text)
        self._input.clear()
        self._input.setFocus()

    def _on_command_double_clicked(self, item: QListWidgetItem):
        cmd = item.data(Qt.ItemDataRole.UserRole)
        self._input.setText(cmd)
        self._input.setFocus()

    def _on_log(self, entry: str):
        t = ThemeManager.instance().theme
        safe = _html.escape(entry)
        if ">>" in entry:
            color = t.log_output
        elif "??" in entry:
            color = t.log_error_tag
        elif "<<" in entry:
            color = t.log_input
        elif "BŁĄD" in entry:
            color = t.log_error
        elif "Połączono" in entry or "Rozłączono" in entry:
            color = t.log_connection
        else:
            color = t.log_default
        self._log_view.appendHtml(
            f'<pre style="margin:0; color:{color}; font-family:monospace; font-size:9pt;">'
            f'{safe}</pre>'
        )

    def _on_connection_changed(self, connected: bool):
        self._send_btn.setEnabled(connected)
        self._input.setEnabled(connected)
        self._input.setPlaceholderText(
            "np. S, SI, T, Z  —  CR LF dodawane automatycznie"
            if connected else
            "Brak połączenia z wagą"
        )

    def _on_protocol_changed(self, protocol):
        self._rebuild_commands(protocol)

    def _rebuild_commands(self, protocol):
        self._cmd_list.clear()
        for cmd, desc in protocol.command_list:
            item = QListWidgetItem(f"{cmd:<8} {desc}")
            item.setData(Qt.ItemDataRole.UserRole, cmd)
            item.setToolTip(f"{cmd}  —  {desc}")
            self._cmd_list.addItem(item)
