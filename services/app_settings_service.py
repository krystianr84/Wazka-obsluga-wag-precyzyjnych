import json
import sys
from pathlib import Path


def _get_settings_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "app_settings.json"
    return Path(__file__).parent.parent / "app_settings.json"


_SETTINGS_FILE = _get_settings_path()


DEFAULT_INTERVAL_MS = 1000

AVAILABLE_INTERVALS: list[tuple[int, str]] = [
    (250,   "250 ms"),
    (500,   "500 ms"),
    (1000,  "1000 ms — domyślny"),
    (2000,  "2000 ms"),
    (5000,  "5000 ms"),
    (10000, "10 000 ms"),
]


class AppSettingsService:
    def __init__(self):
        self._theme = "dark"
        self._interval_ms = DEFAULT_INTERVAL_MS
        self._load()

    @property
    def theme(self) -> str:
        return self._theme

    def set_theme(self, name: str) -> None:
        self._theme = name
        self._persist()

    @property
    def interval_ms(self) -> int:
        return self._interval_ms

    def set_interval_ms(self, ms: int) -> None:
        self._interval_ms = ms
        self._persist()

    def _load(self) -> None:
        if not _SETTINGS_FILE.exists():
            return
        try:
            with open(_SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self._theme = data.get("theme", "dark")
            self._interval_ms = data.get("interval_ms", DEFAULT_INTERVAL_MS)
        except Exception:
            pass

    def _persist(self) -> None:
        try:
            with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"theme": self._theme, "interval_ms": self._interval_ms},
                    f, indent=2, ensure_ascii=False,
                )
        except Exception:
            pass
