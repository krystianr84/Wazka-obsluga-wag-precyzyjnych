import pytest
from models.weight_reading import WeightStatus
from protocols.sartorius_sbi_protocol import SartoriusSbiProtocol


@pytest.fixture
def proto():
    return SartoriusSbiProtocol()


class TestSartoriusProperties:
    def test_name(self, proto):
        assert proto.name == "Sartorius (SBI)"

    def test_baud_rate(self, proto):
        assert proto.default_baud_rate == 1200

    def test_commands_bytes(self, proto):
        assert proto.weight_command == b"P\r\n"
        assert proto.tare_command == b"T\r\n"
        assert proto.zero_command == b"Z\r\n"

    def test_command_list_not_empty(self, proto):
        assert len(proto.command_list) > 0


class TestSartoriusParse:
    # ── Odczyty stabilne ──────────────────────────────────────────────────

    def test_positive_stable(self, proto):
        r = proto.parse_response("+  50.000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(50.0)
        assert r.unit == "g"

    def test_negative_stable(self, proto):
        r = proto.parse_response("-   0.010 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(-0.010)
        assert r.unit == "g"

    def test_zero_positive(self, proto):
        r = proto.parse_response("+   0.000 g")
        assert r is not None
        assert r.value == pytest.approx(0.0)
        assert r.status == WeightStatus.STABLE

    def test_kilogram_unit(self, proto):
        r = proto.parse_response("+   1.500 kg")
        assert r is not None
        assert r.unit == "kg"
        assert r.value == pytest.approx(1.5)

    def test_comma_decimal(self, proto):
        r = proto.parse_response("+  50,000 g")
        assert r is not None
        assert r.value == pytest.approx(50.0)

    # ── Odczyt dynamiczny ─────────────────────────────────────────────────

    def test_dynamic(self, proto):
        r = proto.parse_response("S  50.000 g")
        assert r is not None
        assert r.status == WeightStatus.DYNAMIC
        assert r.value == pytest.approx(50.0)

    # ── Stany specjalne ───────────────────────────────────────────────────

    def test_in_progress(self, proto):
        r = proto.parse_response("I")
        assert r is not None
        assert r.status == WeightStatus.IN_PROGRESS

    def test_over_range(self, proto):
        r = proto.parse_response("O")
        assert r is not None
        assert r.status == WeightStatus.OVER_RANGE

    def test_error(self, proto):
        r = proto.parse_response("E")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    # ── Bez jednostki ─────────────────────────────────────────────────────

    def test_no_unit(self, proto):
        r = proto.parse_response("+0.000")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(0.0)
        assert r.unit == ""

    # ── Nierozpoznane ─────────────────────────────────────────────────────

    def test_empty_line(self, proto):
        assert proto.parse_response("") is None

    def test_unknown_first_char(self, proto):
        assert proto.parse_response("X  50.000 g") is None

    def test_digit_first(self, proto):
        assert proto.parse_response("50.000 g") is None
