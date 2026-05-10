import html as _html

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QPlainTextEdit, QLabel, QStatusBar, QFrame, QCheckBox, QMenu,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QAction

from services.scale_service import ScaleService, AVAILABLE_PROTOCOLS, PARITY_OPTIONS, DATA_BITS_OPTIONS, STOP_BITS_OPTIONS
from services.preset_service import PresetService
from services.app_settings_service import AppSettingsService
from ui.theme import ThemeManager, ThemeColors
from ui.weight_display import WeightDisplay
from ui.settings_dialog import SettingsDialog
from ui.about_dialog import AboutDialog
from ui.terminal_dialog import TerminalDialog
from ui.app_settings_dialog import AppSettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, app_settings_service: AppSettingsService):
        super().__init__()
        self.setWindowTitle("Ważka — Komunikacja z wagami")
        self.setMinimumWidth(900)

        self._app_settings_service = app_settings_service
        self._is_connected = False

        self._service = ScaleService(self)
        self._service.set_continuous_interval(app_settings_service.interval_ms)
        self._preset_service = PresetService()

        self._service.reading_updated.connect(self._on_reading)
        self._service.log_added.connect(self._on_log)
        self._service.connection_changed.connect(self._on_connection_changed)
        self._service.error_occurred.connect(self._on_error)
        self._service.session_stats_updated.connect(self._on_stats_updated)
        self._service.session_stats_reset.connect(self._on_stats_reset)

        self._settings_dialog = SettingsDialog(self._service, self._preset_service, self)
        self._terminal_dialog = TerminalDialog(self._service, self)
        self._service.continuous_changed.connect(self._on_continuous_changed)

        self._build_menu()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(12, 12, 12, 12)

        root.addWidget(self._build_connection_bar())
        root.addWidget(self._build_weight_display())
        root.addLayout(self._build_command_buttons())
        root.addLayout(self._build_log_header())
        root.addWidget(self._build_log_view(), stretch=1)

        self._log_view.setVisible(False)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Rozłączono")

        self._set_commands_enabled(False)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    # ── Budowanie UI ──────────────────────────────────────────────────────

    def _build_menu(self):
        menu_bar = self.menuBar()

        scale_menu = menu_bar.addMenu("Waga")

        settings_action = QAction("Ustawienia połączenia...", self)
        settings_action.setShortcut("Ctrl+U")
        settings_action.triggered.connect(self._open_settings)
        scale_menu.addAction(settings_action)

        terminal_action = QAction("Terminal...", self)
        terminal_action.setShortcut("Ctrl+T")
        terminal_action.triggered.connect(self._open_terminal)
        scale_menu.addAction(terminal_action)

        scale_menu.addSeparator()

        app_settings_action = QAction("Opcje aplikacji...", self)
        app_settings_action.setShortcut("Ctrl+,")
        app_settings_action.triggered.connect(self._open_app_settings)
        scale_menu.addAction(app_settings_action)

        scale_menu.addSeparator()

        quit_action = QAction("Zakończ", self)
        quit_action.setShortcut("Alt+F4")
        quit_action.triggered.connect(self.close)
        scale_menu.addAction(quit_action)

        help_menu = menu_bar.addMenu("Pomoc")

        about_action = QAction("O programie...", self)
        about_action.setShortcut("F1")
        about_action.triggered.connect(self._open_about)
        help_menu.addAction(about_action)

    def _build_connection_bar(self) -> QFrame:
        self._conn_bar = QFrame()
        self._conn_bar.setFixedHeight(42)
        layout = QHBoxLayout(self._conn_bar)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(10)

        self._conn_dot = QLabel("●")
        self._conn_dot.setStyleSheet("font-size: 14px; border: none;")

        self._conn_label = QLabel("Rozłączono")
        self._conn_label.setStyleSheet("font-size: 12px; border: none;")

        self._quick_btn = QPushButton("⚡ Profile ▾")
        self._quick_btn.setFixedHeight(28)
        self._quick_btn.clicked.connect(self._show_quick_menu)

        self._settings_bar_btn = QPushButton("Ustawienia połączenia...")
        self._settings_bar_btn.setFixedHeight(28)
        self._settings_bar_btn.clicked.connect(self._open_settings)

        layout.addWidget(self._conn_dot)
        layout.addWidget(self._conn_label, stretch=1)
        layout.addWidget(self._quick_btn)
        layout.addWidget(self._settings_bar_btn)
        return self._conn_bar

    def _build_weight_display(self) -> WeightDisplay:
        self._weight_display = WeightDisplay()
        return self._weight_display

    def _build_command_buttons(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self._btn_weight = self._make_cmd_btn("Odczyt wagi", self._service.request_weight)
        self._btn_weight_now = self._make_cmd_btn("Odczyt natychmiastowy", self._service.request_weight_immediate)
        self._btn_tare = self._make_cmd_btn("TARA", self._service.tare)
        self._btn_zero = self._make_cmd_btn("ZERO", self._service.zero)
        self._btn_continuous = self._make_toggle_btn("Odczyt ciągły")
        self._btn_continuous.toggled.connect(self._on_continuous_toggled)

        for btn in (self._btn_weight, self._btn_weight_now,
                    self._btn_continuous, self._btn_tare, self._btn_zero):
            layout.addWidget(btn)
        return layout

    def _build_log_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)
        label = QLabel("Log komunikacji:")
        self._chk_log = QCheckBox("Pokaż")
        self._chk_log.setChecked(False)
        self._chk_log.toggled.connect(self._on_log_visibility_changed)
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(self._chk_log)
        return layout

    def _build_log_view(self) -> QPlainTextEdit:
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont("Courier New", 9))
        self._log_view.setMaximumBlockCount(200)
        return self._log_view

    # ── Motyw ──────────────────────────────────────────────────────────────

    def _apply_theme(self):
        t = ThemeManager.instance().theme

        self._conn_bar.setStyleSheet(
            f"QFrame {{ background-color: {t.bg_window}; border-radius: 6px; "
            f"border: 1px solid {t.border}; }}"
        )
        self._quick_btn.setStyleSheet(
            f"QPushButton {{ background-color: {t.btn_profiles_bg}; color: {t.btn_profiles_fg}; "
            f"border: 1px solid {t.btn_profiles_border}; border-radius: 4px; padding: 0 10px; }}"
            f"QPushButton:hover {{ background-color: {t.btn_profiles_hover}; }}"
            f"QPushButton:disabled {{ background-color: {t.bg_input}; color: {t.text_disabled}; "
            f"border: 1px solid {t.border}; }}"
        )
        self._settings_bar_btn.setStyleSheet(
            f"QPushButton {{ background-color: {t.bg_input}; color: {t.text}; "
            f"border: 1px solid {t.border_light}; border-radius: 4px; padding: 0 10px; }}"
            f"QPushButton:hover {{ background-color: {t.bg_input_hover}; }}"
        )

        # Wskaźnik połączenia — zachowaj aktualny stan
        if self._is_connected:
            self._conn_dot.setStyleSheet(f"color: {t.dot_connected}; font-size: 14px; border: none;")
            self._conn_label.setStyleSheet(f"color: {t.text}; font-size: 12px; border: none;")
        else:
            self._conn_dot.setStyleSheet(f"color: {t.dot_idle}; font-size: 14px; border: none;")
            self._conn_label.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; border: none;")

        self._set_cmd_btn_style(self._btn_weight, t.btn_weight, t)
        self._set_cmd_btn_style(self._btn_weight_now, t.btn_weight_now, t)
        self._set_cmd_btn_style(self._btn_tare, t.btn_tare, t)
        self._set_cmd_btn_style(self._btn_zero, t.btn_zero, t)
        self._set_toggle_btn_style(self._btn_continuous, t.btn_continuous_off, t.btn_continuous_on, t)

        self._log_view.setStyleSheet(
            f"background-color: {t.bg_panel}; color: {t.text}; border-radius: 4px;"
        )

    # ── Sloty ─────────────────────────────────────────────────────────────

    def _open_settings(self):
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def _open_terminal(self):
        self._terminal_dialog.show()
        self._terminal_dialog.raise_()
        self._terminal_dialog.activateWindow()

    def _open_about(self):
        AboutDialog(self).exec()

    def _open_app_settings(self):
        dlg = AppSettingsDialog(self._app_settings_service, self._service, self)
        dlg.exec()

    def _show_quick_menu(self):
        presets = self._preset_service.presets
        menu = QMenu(self)
        if presets:
            for preset in presets:
                action = QAction(preset.name, self)
                action.triggered.connect(lambda checked, p=preset: self._connect_preset(p))
                menu.addAction(action)
        else:
            empty = QAction("Brak zapisanych profili", self)
            empty.setEnabled(False)
            menu.addAction(empty)
        menu.exec(self._quick_btn.mapToGlobal(
            self._quick_btn.rect().bottomLeft()
        ))

    def _connect_preset(self, preset):
        if self._service.is_connected:
            return
        for p in AVAILABLE_PROTOCOLS:
            if p.name == preset.protocol_name:
                self._service.set_protocol(p)
                break
        self._service.connect(
            preset.port,
            preset.baud_rate,
            PARITY_OPTIONS[preset.parity],
            DATA_BITS_OPTIONS[preset.data_bits],
            STOP_BITS_OPTIONS[preset.stop_bits],
        )

    def _on_reading(self, reading):
        try:
            self._weight_display.update_reading(reading)
        except Exception as e:
            self._service._add_log(f"BŁĄD wyświetlania: {e!r}")

    def _on_stats_updated(self, min_val: float, max_val: float, mean: float, stddev: float, unit: str):
        self._weight_display.update_stats(min_val, max_val, mean, stddev, unit)

    def _on_stats_reset(self):
        self._weight_display.reset_stats()

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
        self._is_connected = connected
        t = ThemeManager.instance().theme
        self._set_commands_enabled(connected)
        self._quick_btn.setEnabled(not connected)
        if connected:
            self._conn_dot.setStyleSheet(f"color: {t.dot_connected}; font-size: 14px; border: none;")
            self._conn_label.setStyleSheet(f"color: {t.text}; font-size: 12px; border: none;")
            self._conn_label.setText(self._service.connection_info)
            self._status_bar.showMessage("Połączono")
        else:
            self._conn_dot.setStyleSheet(f"color: {t.dot_idle}; font-size: 14px; border: none;")
            self._conn_label.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; border: none;")
            self._conn_label.setText("Rozłączono")
            self._status_bar.showMessage("Rozłączono")

    def _on_error(self, msg: str):
        t = ThemeManager.instance().theme
        self._conn_dot.setStyleSheet(f"color: {t.dot_error}; font-size: 14px; border: none;")
        self._status_bar.showMessage(f"Błąd: {msg}")

    def _on_log_visibility_changed(self, visible: bool):
        self._log_view.setVisible(visible)
        if visible:
            self.setMinimumHeight(620)
            self.resize(self.width(), max(self.height(), 620))
        else:
            self.setMinimumHeight(0)
            QTimer.singleShot(0, lambda: self.resize(self.width(), self.sizeHint().height()))

    def _on_continuous_toggled(self, checked: bool):
        if checked:
            self._service.start_continuous()
        else:
            self._service.stop_continuous()

    def _on_continuous_changed(self, active: bool):
        self._btn_continuous.blockSignals(True)
        self._btn_continuous.setChecked(active)
        self._btn_continuous.blockSignals(False)

    def _set_commands_enabled(self, enabled: bool):
        for btn in (self._btn_weight, self._btn_weight_now,
                    self._btn_tare, self._btn_zero, self._btn_continuous):
            btn.setEnabled(enabled)
        if not enabled:
            self._btn_continuous.blockSignals(True)
            self._btn_continuous.setChecked(False)
            self._btn_continuous.blockSignals(False)

    # ── Fabryki przycisków ────────────────────────────────────────────────

    @staticmethod
    def _make_cmd_btn(label: str, slot) -> QPushButton:
        btn = QPushButton(label)
        btn.setMinimumHeight(42)
        btn.clicked.connect(slot)
        return btn

    @staticmethod
    def _make_toggle_btn(label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setMinimumHeight(42)
        btn.setCheckable(True)
        return btn

    @staticmethod
    def _set_cmd_btn_style(btn: QPushButton, color: str, t: ThemeColors) -> None:
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: white; "
            f"border-radius: 5px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: {color}cc; }}"
            f"QPushButton:disabled {{ background-color: {t.btn_disabled_bg}; "
            f"color: {t.btn_disabled_fg}; }}"
        )

    @staticmethod
    def _set_toggle_btn_style(btn: QPushButton, color_off: str, color_on: str, t: ThemeColors) -> None:
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {color_off}; color: white; "
            f"border-radius: 5px; font-weight: bold; }}"
            f"QPushButton:checked {{ background-color: {color_on}; "
            f"border: 2px solid #7986cb; }}"
            f"QPushButton:hover {{ background-color: {color_off}cc; }}"
            f"QPushButton:checked:hover {{ background-color: {color_on}cc; }}"
            f"QPushButton:disabled {{ background-color: {t.btn_disabled_bg}; "
            f"color: {t.btn_disabled_fg}; }}"
        )
