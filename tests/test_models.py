import pytest
from datetime import datetime

from models.weight_reading import WeightReading, WeightStatus, STATUS_LABELS
from models.scale_preset import ScalePreset


class TestWeightStatus:
    def test_all_values_exist(self):
        statuses = {
            WeightStatus.STABLE, WeightStatus.DYNAMIC, WeightStatus.OVER_RANGE,
            WeightStatus.UNDER_RANGE, WeightStatus.IN_PROGRESS, WeightStatus.ERROR,
        }
        assert len(statuses) == 6

    def test_all_statuses_have_labels(self):
        for status in WeightStatus:
            assert status in STATUS_LABELS
            assert isinstance(STATUS_LABELS[status], str)


class TestWeightReading:
    def test_formatted_value(self):
        r = WeightReading(value=50.0, unit="g", status=WeightStatus.STABLE)
        assert r.formatted_value == "50.000 g"

    def test_formatted_value_negative(self):
        r = WeightReading(value=-1.5, unit="kg", status=WeightStatus.STABLE)
        assert r.formatted_value == "-1.500 kg"

    def test_formatted_value_zero(self):
        r = WeightReading(value=0.0, unit="g", status=WeightStatus.STABLE)
        assert r.formatted_value == "0.000 g"

    def test_status_label(self):
        r = WeightReading(value=0.0, unit="g", status=WeightStatus.STABLE)
        assert r.status_label == STATUS_LABELS[WeightStatus.STABLE]

    def test_timestamp_auto_set(self):
        before = datetime.now()
        r = WeightReading(value=1.0, unit="g", status=WeightStatus.STABLE)
        after = datetime.now()
        assert before <= r.timestamp <= after

    def test_timestamp_manual(self):
        ts = datetime(2026, 1, 15, 12, 0, 0)
        r = WeightReading(value=1.0, unit="g", status=WeightStatus.STABLE, timestamp=ts)
        assert r.timestamp == ts

    def test_all_status_labels_are_strings(self):
        for status in WeightStatus:
            r = WeightReading(value=0.0, unit="g", status=status)
            assert isinstance(r.status_label, str)
            assert len(r.status_label) > 0


class TestScalePreset:
    def test_fields(self):
        p = ScalePreset(
            name="Waga lab",
            protocol_name="Mettler Toledo (MT-SICS)",
            port="COM3",
            baud_rate=9600,
            parity="Brak (N)",
            data_bits="8",
            stop_bits="1",
        )
        assert p.name == "Waga lab"
        assert p.protocol_name == "Mettler Toledo (MT-SICS)"
        assert p.port == "COM3"
        assert p.baud_rate == 9600
        assert p.parity == "Brak (N)"
        assert p.data_bits == "8"
        assert p.stop_bits == "1"
