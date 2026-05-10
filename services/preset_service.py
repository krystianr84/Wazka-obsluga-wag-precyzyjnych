import dataclasses
import json
import sys
from pathlib import Path

from models.scale_preset import ScalePreset


def _get_presets_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "presets.json"
    return Path(__file__).parent.parent / "presets.json"


_PRESETS_FILE = _get_presets_path()


class PresetService:
    def __init__(self):
        self._presets: list[ScalePreset] = []
        self._load()

    @property
    def presets(self) -> list[ScalePreset]:
        return list(self._presets)

    def save_preset(self, preset: ScalePreset):
        for i, p in enumerate(self._presets):
            if p.name == preset.name:
                self._presets[i] = preset
                self._persist()
                return
        self._presets.append(preset)
        self._persist()

    def delete_preset(self, name: str):
        self._presets = [p for p in self._presets if p.name != name]
        self._persist()

    def _load(self):
        if not _PRESETS_FILE.exists():
            return
        try:
            with open(_PRESETS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self._presets = [ScalePreset(**d) for d in data]
        except Exception:
            self._presets = []

    def _persist(self):
        try:
            with open(_PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    [dataclasses.asdict(p) for p in self._presets],
                    f, indent=2, ensure_ascii=False,
                )
        except Exception:
            pass
