from dataclasses import dataclass

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPalette, QColor


@dataclass(frozen=True)
class ThemeColors:
    name: str

    bg_window: str
    bg_panel: str
    bg_display: str
    bg_input: str
    bg_input_hover: str
    bg_list: str

    border: str
    border_light: str

    text: str
    text_secondary: str
    text_muted: str
    text_dim: str
    text_disabled: str

    btn_disabled_bg: str
    btn_disabled_fg: str

    status_stable: str
    status_dynamic: str
    status_error: str
    status_progress: str
    status_default: str

    btn_weight: str
    btn_weight_now: str
    btn_tare: str
    btn_zero: str
    btn_continuous_off: str
    btn_continuous_on: str
    btn_connect: str
    btn_connect_hover: str
    btn_disconnect: str
    btn_disconnect_hover: str
    btn_profiles_bg: str
    btn_profiles_fg: str
    btn_profiles_border: str
    btn_profiles_hover: str

    log_output: str
    log_error_tag: str
    log_input: str
    log_error: str
    log_connection: str
    log_default: str

    dot_connected: str
    dot_idle: str
    dot_error: str

    delete_fg: str
    delete_hover: str


DARK = ThemeColors(
    name="dark",
    bg_window="#1e1e1e",
    bg_panel="#1a1a1a",
    bg_display="#111111",
    bg_input="#2a2a2a",
    bg_input_hover="#333333",
    bg_list="#1e1e1e",
    border="#2a2a2a",
    border_light="#3a3a3a",
    text="#cccccc",
    text_secondary="#aaaaaa",
    text_muted="#888888",
    text_dim="#666666",
    text_disabled="#555555",
    btn_disabled_bg="#444444",
    btn_disabled_fg="#888888",
    status_stable="#00e676",
    status_dynamic="#ffa726",
    status_error="#ef5350",
    status_progress="#42a5f5",
    status_default="#9e9e9e",
    btn_weight="#1565c0",
    btn_weight_now="#0277bd",
    btn_tare="#e65100",
    btn_zero="#6a1b9a",
    btn_continuous_off="#1a237e",
    btn_continuous_on="#3949ab",
    btn_connect="#2e7d32",
    btn_connect_hover="#388e3c",
    btn_disconnect="#c62828",
    btn_disconnect_hover="#d32f2f",
    btn_profiles_bg="#1a3a1a",
    btn_profiles_fg="#81c784",
    btn_profiles_border="#2e5e2e",
    btn_profiles_hover="#223322",
    log_output="#64b5f6",
    log_error_tag="#ff8a65",
    log_input="#81c784",
    log_error="#ef5350",
    log_connection="#fff176",
    log_default="#cccccc",
    dot_connected="#00e676",
    dot_idle="#555555",
    dot_error="#ef5350",
    delete_fg="#ef9a9a",
    delete_hover="#ef5350",
)

LIGHT = ThemeColors(
    name="light",
    bg_window="#f5f5f5",
    bg_panel="#ffffff",
    bg_display="#eeeeee",
    bg_input="#e0e0e0",
    bg_input_hover="#d5d5d5",
    bg_list="#fafafa",
    border="#cccccc",
    border_light="#bdbdbd",
    text="#212121",
    text_secondary="#555555",
    text_muted="#757575",
    text_dim="#9e9e9e",
    text_disabled="#bdbdbd",
    btn_disabled_bg="#e0e0e0",
    btn_disabled_fg="#9e9e9e",
    status_stable="#2e7d32",
    status_dynamic="#e65100",
    status_error="#c62828",
    status_progress="#1565c0",
    status_default="#757575",
    btn_weight="#1565c0",
    btn_weight_now="#0277bd",
    btn_tare="#e65100",
    btn_zero="#6a1b9a",
    btn_continuous_off="#1a237e",
    btn_continuous_on="#3949ab",
    btn_connect="#2e7d32",
    btn_connect_hover="#388e3c",
    btn_disconnect="#c62828",
    btn_disconnect_hover="#d32f2f",
    btn_profiles_bg="#e8f5e9",
    btn_profiles_fg="#2e7d32",
    btn_profiles_border="#a5d6a7",
    btn_profiles_hover="#c8e6c9",
    log_output="#1565c0",
    log_error_tag="#bf360c",
    log_input="#2e7d32",
    log_error="#c62828",
    log_connection="#e65100",
    log_default="#212121",
    dot_connected="#2e7d32",
    dot_idle="#9e9e9e",
    dot_error="#c62828",
    delete_fg="#c62828",
    delete_hover="#b71c1c",
)

THEMES: dict[str, ThemeColors] = {"dark": DARK, "light": LIGHT}


class ThemeManager(QObject):
    theme_changed = pyqtSignal()

    _instance: "ThemeManager | None" = None

    def __init__(self):
        super().__init__()
        self._current = DARK

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def initialize(cls, theme_name: str) -> "ThemeManager":
        inst = cls.instance()
        if theme_name in THEMES:
            inst._current = THEMES[theme_name]
        return inst

    @property
    def theme(self) -> ThemeColors:
        return self._current

    def set_theme(self, name: str) -> None:
        if name not in THEMES or self._current.name == name:
            return
        self._current = THEMES[name]
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.setPalette(self._build_palette())
        self.theme_changed.emit()

    def build_initial_palette(self) -> QPalette:
        return self._build_palette()

    def _build_palette(self) -> QPalette:
        t = self._current
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(t.bg_window))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(t.text))
        palette.setColor(QPalette.ColorRole.Base, QColor(t.bg_panel))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(t.bg_input))
        palette.setColor(QPalette.ColorRole.Text, QColor(t.text))
        palette.setColor(QPalette.ColorRole.Button, QColor(t.bg_input))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(t.text))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(t.btn_weight))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(t.bg_panel))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(t.text))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(t.text_dim))
        disabled = palette.brush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText)
        palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t.text_disabled)
        )
        palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t.text_disabled)
        )
        return palette
