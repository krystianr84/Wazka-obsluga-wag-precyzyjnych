import pytest
from models.weight_reading import WeightStatus
from protocols.mettler_sics_protocol import MettlerSicsProtocol


@pytest.fixture
def proto():
    return MettlerSicsProtocol()


class TestMettlerSicsProperties:
    def test_name(self, proto):
        assert proto.name == "Mettler Toledo (MT-SICS)"

    def test_baud_rate(self, proto):
        assert proto.default_baud_rate == 9600

    def test_commands_bytes(self, proto):
        assert proto.weight_command == b"S\r\n"
        assert proto.weight_immediate_command == b"SI\r\n"
        assert proto.tare_command == b"T\r\n"
        assert proto.zero_command == b"Z\r\n"

    def test_command_list_not_empty(self, proto):
        assert len(proto.command_list) > 0
        for cmd, desc in proto.command_list:
            assert isinstance(cmd, str)
            assert isinstance(desc, str)


class TestMettlerSicsParse:
    # ── Odczyty z wagą ────────────────────────────────────────────────────

    def test_stable_reading(self, proto):
        r = proto.parse_response("S S     50.000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(50.0)
        assert r.unit == "g"

    def test_dynamic_reading(self, proto):
        r = proto.parse_response("S D     50.000 g")
        assert r is not None
        assert r.status == WeightStatus.DYNAMIC
        assert r.value == pytest.approx(50.0)

    def test_stable_zero(self, proto):
        r = proto.parse_response("S S      0.000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(0.0)

    def test_kilogram_unit(self, proto):
        r = proto.parse_response("S S      1.500 kg")
        assert r is not None
        assert r.unit == "kg"
        assert r.value == pytest.approx(1.5)

    def test_negative_value(self, proto):
        r = proto.parse_response("S S     -0.010 g")
        assert r is not None
        assert r.value == pytest.approx(-0.01)

    def test_comma_decimal_separator(self, proto):
        r = proto.parse_response("S S     50,000 g")
        assert r is not None
        assert r.value == pytest.approx(50.0)

    # ── Tara ──────────────────────────────────────────────────────────────

    def test_tare_done(self, proto):
        r = proto.parse_response("T S      0.000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(0.0)

    def test_tare_in_progress_no_value(self, proto):
        r = proto.parse_response("T I")
        assert r is not None
        assert r.status == WeightStatus.IN_PROGRESS

    # ── Zerowanie ─────────────────────────────────────────────────────────

    def test_zero_ack(self, proto):
        r = proto.parse_response("Z A")
        assert r is not None
        assert r.status == WeightStatus.STABLE

    def test_zero_in_progress(self, proto):
        r = proto.parse_response("Z I")
        assert r is not None
        assert r.status == WeightStatus.IN_PROGRESS

    # ── Zakresy ───────────────────────────────────────────────────────────

    def test_over_range(self, proto):
        r = proto.parse_response("S +")
        assert r is not None
        assert r.status == WeightStatus.OVER_RANGE

    def test_under_range(self, proto):
        r = proto.parse_response("S -")
        assert r is not None
        assert r.status == WeightStatus.UNDER_RANGE

    def test_zero_over_range(self, proto):
        r = proto.parse_response("Z +")
        assert r is not None
        assert r.status == WeightStatus.OVER_RANGE

    # ── Błędy ─────────────────────────────────────────────────────────────

    def test_syntax_error_ES(self, proto):
        r = proto.parse_response("ES")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    def test_syntax_error_ET(self, proto):
        r = proto.parse_response("ET")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    def test_syntax_error_EZ(self, proto):
        r = proto.parse_response("EZ")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    # ── Nierozpoznane ─────────────────────────────────────────────────────

    def test_empty_line(self, proto):
        assert proto.parse_response("") is None

    def test_whitespace_only(self, proto):
        assert proto.parse_response("   ") is None

    def test_unknown_command(self, proto):
        assert proto.parse_response("XYZ") is None

    def test_too_few_parts(self, proto):
        assert proto.parse_response("S") is None
