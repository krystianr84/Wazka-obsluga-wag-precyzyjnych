from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame

from models.weight_reading import WeightReading, WeightStatus
from ui.theme import ThemeManager, ThemeColors

_STATUS_LABELS = {
    WeightStatus.STABLE: "STABILNA",
    WeightStatus.DYNAMIC: "DYNAMICZNA",
    WeightStatus.OVER_RANGE: "PRZEKROCZONY ZAKRES",
    WeightStatus.UNDER_RANGE: "PONIŻEJ ZAKRESU",
    WeightStatus.IN_PROGRESS: "W TRAKCIE...",
    WeightStatus.ERROR: "BŁĄD",
}

_SPECIAL_VALUES = {
    WeightStatus.OVER_RANGE: "> MAX",
    WeightStatus.UNDER_RANGE: "< MIN",
    WeightStatus.ERROR: "ERR",
    WeightStatus.IN_PROGRESS: "...",
}


def _status_color(status: WeightStatus, t: ThemeColors) -> str:
    return {
        WeightStatus.STABLE: t.status_stable,
        WeightStatus.DYNAMIC: t.status_dynamic,
        WeightStatus.OVER_RANGE: t.status_error,
        WeightStatus.UNDER_RANGE: t.status_error,
        WeightStatus.IN_PROGRESS: t.status_progress,
        WeightStatus.ERROR: t.status_error,
    }[status]


class WeightDisplay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)

        self._last_reading: WeightReading | None = None
        self._stats_active = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 12)

        self._value_label = QLabel("--- ---")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._value_label.setFont(QFont("Courier New", 48, QFont.Weight.Bold))

        bottom = QHBoxLayout()
        self._status_label = QLabel("BRAK DANYCH")
        self._time_label = QLabel("")
        self._time_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        bottom.addWidget(self._status_label)
        bottom.addStretch()
        bottom.addWidget(self._time_label)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        self._min_label = QLabel("Min: ---")
        self._max_label = QLabel("Max: ---")
        self._mean_label = QLabel("Śr: ---")
        self._stddev_label = QLabel("σ: ---")

        stats_row.addStretch()
        stats_row.addWidget(self._min_label)
        stats_row.addWidget(self._max_label)
        stats_row.addWidget(self._mean_label)
        stats_row.addWidget(self._stddev_label)
        stats_row.addStretch()

        layout.addWidget(self._value_label)
        layout.addLayout(bottom)
        layout.addLayout(stats_row)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def update_reading(self, reading: WeightReading):
        self._last_reading = reading
        t = ThemeManager.instance().theme
        color = _status_color(reading.status, t)

        self._value_label.setText(_SPECIAL_VALUES.get(reading.status, reading.formatted_value))
        self._value_label.setStyleSheet(f"color: {color};")

        self._status_label.setText(_STATUS_LABELS[reading.status])
        self._status_label.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold;"
            f"border: 1px solid {color}; padding: 2px 6px; border-radius: 3px;"
        )
        self._time_label.setText(reading.timestamp.strftime("%H:%M:%S"))

    def update_stats(self, min_val: float, max_val: float, mean: float, stddev: float, unit: str):
        self._stats_active = True
        t = ThemeManager.instance().theme
        self._min_label.setText(f"Min: {min_val:.3f} {unit}")
        self._max_label.setText(f"Max: {max_val:.3f} {unit}")
        self._mean_label.setText(f"Śr: {mean:.3f} {unit}")
        self._stddev_label.setText(f"σ: {stddev:.3f} {unit}")
        style = f"color: {t.text_secondary}; font-size: 11px;"
        for lbl in (self._min_label, self._max_label, self._mean_label, self._stddev_label):
            lbl.setStyleSheet(style)

    def reset_stats(self):
        self._stats_active = False
        t = ThemeManager.instance().theme
        for lbl, text in (
            (self._min_label, "Min: ---"),
            (self._max_label, "Max: ---"),
            (self._mean_label, "Śr: ---"),
            (self._stddev_label, "σ: ---"),
        ):
            lbl.setText(text)
            lbl.setStyleSheet(f"color: {t.text_dim}; font-size: 11px;")

    def _apply_theme(self):
        t = ThemeManager.instance().theme
        self.setStyleSheet(f"background-color: {t.bg_display}; border-radius: 8px;")
        self._time_label.setStyleSheet(f"color: {t.text_dim}; font-size: 11px;")

        if self._last_reading is not None:
            self.update_reading(self._last_reading)
        else:
            self._value_label.setStyleSheet(f"color: {t.status_default};")
            self._status_label.setStyleSheet(
                f"color: {t.status_default}; font-size: 11px; font-weight: bold;"
                f"border: 1px solid {t.status_default}; padding: 2px 6px; border-radius: 3px;"
            )

        if self._stats_active:
            style = f"color: {t.text_secondary}; font-size: 11px;"
        else:
            style = f"color: {t.text_dim}; font-size: 11px;"
        for lbl in (self._min_label, self._max_label, self._mean_label, self._stddev_label):
            lbl.setStyleSheet(style)
