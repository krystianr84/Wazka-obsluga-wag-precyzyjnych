import json
import pytest

import services.preset_service as ps_module
from services.preset_service import PresetService
from models.scale_preset import ScalePreset


def _make_preset(name="Waga lab", port="COM3", baud=9600) -> ScalePreset:
    return ScalePreset(
        name=name,
        protocol_name="Mettler Toledo (MT-SICS)",
        port=port,
        baud_rate=baud,
        parity="Brak (N)",
        data_bits="8",
        stop_bits="1",
    )


@pytest.fixture(autouse=True)
def patch_presets_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ps_module, "_PRESETS_FILE", tmp_path / "presets.json")


class TestPresetServiceLoad:
    def test_empty_on_missing_file(self):
        svc = PresetService()
        assert svc.presets == []

    def test_load_from_existing_file(self, tmp_path):
        data = [
            {
                "name": "Waga A",
                "protocol_name": "Sartorius (SBI)",
                "port": "COM1",
                "baud_rate": 1200,
                "parity": "Brak (N)",
                "data_bits": "8",
                "stop_bits": "1",
            }
        ]
        (tmp_path / "presets.json").write_text(json.dumps(data), encoding="utf-8")
        svc = PresetService()
        assert len(svc.presets) == 1
        assert svc.presets[0].name == "Waga A"
        assert svc.presets[0].baud_rate == 1200

    def test_corrupted_file_gives_empty_list(self, tmp_path):
        (tmp_path / "presets.json").write_text("NIE JSON", encoding="utf-8")
        svc = PresetService()
        assert svc.presets == []


class TestPresetServiceSave:
    def test_save_new_preset(self):
        svc = PresetService()
        p = _make_preset("Waga lab")
        svc.save_preset(p)
        assert len(svc.presets) == 1
        assert svc.presets[0].name == "Waga lab"

    def test_save_multiple_presets(self):
        svc = PresetService()
        svc.save_preset(_make_preset("A"))
        svc.save_preset(_make_preset("B"))
        svc.save_preset(_make_preset("C"))
        assert len(svc.presets) == 3

    def test_save_updates_existing_by_name(self):
        svc = PresetService()
        svc.save_preset(_make_preset("Waga", port="COM1", baud=9600))
        svc.save_preset(_make_preset("Waga", port="COM5", baud=19200))
        assert len(svc.presets) == 1
        assert svc.presets[0].port == "COM5"
        assert svc.presets[0].baud_rate == 19200

    def test_presets_property_returns_copy(self):
        svc = PresetService()
        svc.save_preset(_make_preset())
        copy = svc.presets
        copy.clear()
        assert len(svc.presets) == 1


class TestPresetServiceDelete:
    def test_delete_existing(self):
        svc = PresetService()
        svc.save_preset(_make_preset("A"))
        svc.save_preset(_make_preset("B"))
        svc.delete_preset("A")
        names = [p.name for p in svc.presets]
        assert "A" not in names
        assert "B" in names

    def test_delete_nonexistent_is_noop(self):
        svc = PresetService()
        svc.save_preset(_make_preset("A"))
        svc.delete_preset("NIEISTNIEJACA")
        assert len(svc.presets) == 1

    def test_delete_last(self):
        svc = PresetService()
        svc.save_preset(_make_preset("A"))
        svc.delete_preset("A")
        assert svc.presets == []


class TestPresetServicePersistence:
    def test_saved_preset_persists_to_disk(self, tmp_path):
        svc = PresetService()
        svc.save_preset(_make_preset("Trwały"))

        svc2 = PresetService()
        assert len(svc2.presets) == 1
        assert svc2.presets[0].name == "Trwały"

    def test_deleted_preset_removed_from_disk(self, tmp_path):
        svc = PresetService()
        svc.save_preset(_make_preset("A"))
        svc.save_preset(_make_preset("B"))
        svc.delete_preset("A")

        svc2 = PresetService()
        names = [p.name for p in svc2.presets]
        assert "A" not in names
        assert "B" in names

    def test_json_file_is_valid_after_save(self, tmp_path):
        svc = PresetService()
        svc.save_preset(_make_preset("Test JSON"))
        content = (tmp_path / "presets.json").read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, list)
        assert data[0]["name"] == "Test JSON"

    def test_all_preset_fields_persisted(self, tmp_path):
        preset = _make_preset("Pełny", port="COM7", baud=19200)
        preset.parity = "Parzysta (E)"
        preset.data_bits = "7"
        preset.stop_bits = "2"
        svc = PresetService()
        svc.save_preset(preset)

        svc2 = PresetService()
        p = svc2.presets[0]
        assert p.port == "COM7"
        assert p.baud_rate == 19200
        assert p.parity == "Parzysta (E)"
        assert p.data_bits == "7"
        assert p.stop_bits == "2"
