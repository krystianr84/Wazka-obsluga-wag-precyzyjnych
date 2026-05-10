import pytest
from models.weight_reading import WeightStatus
from protocols.radwag_protocol import RadwagProtocol


@pytest.fixture
def proto():
    return RadwagProtocol()


class TestRadwagProperties:
    def test_name(self, proto):
        assert proto.name == "Radwag (WLY / R protocol)"

    def test_baud_rate(self, proto):
        assert proto.default_baud_rate == 9600

    def test_commands_bytes(self, proto):
        assert proto.weight_command == b"SU\r\n"
        assert proto.weight_immediate_command == b"SI\r\n"
        assert proto.tare_command == b"T\r\n"
        assert proto.zero_command == b"Z\r\n"

    def test_command_list_not_empty(self, proto):
        assert len(proto.command_list) > 0


class TestRadwagParse:
    # ── Format z przecinkami ──────────────────────────────────────────────

    def test_stable_comma_format(self, proto):
        r = proto.parse_response("ST,GS,+   50.000000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(50.0)
        assert r.unit == "g"

    def test_dynamic_comma_format(self, proto):
        r = proto.parse_response("US,GS,+   50.000000 g")
        assert r is not None
        assert r.status == WeightStatus.DYNAMIC

    def test_in_progress_comma_format(self, proto):
        r = proto.parse_response("OI,GS,+   50.000000 g")
        assert r is not None
        assert r.status == WeightStatus.IN_PROGRESS

    def test_negative_netto(self, proto):
        r = proto.parse_response("ST,NT,-    0.000000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(0.0)

    def test_comma_decimal_separator(self, proto):
        r = proto.parse_response("ST,GS,+   50,000000 g")
        assert r is not None
        assert r.value == pytest.approx(50.0)

    # ── Format ze spacjami ────────────────────────────────────────────────

    def test_stable_space_format(self, proto):
        r = proto.parse_response("ST +      50.000000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(50.0)

    def test_dynamic_space_format(self, proto):
        r = proto.parse_response("US +      50.000000 g")
        assert r is not None
        assert r.status == WeightStatus.DYNAMIC

    def test_kilogram_unit(self, proto):
        r = proto.parse_response("ST,GS,+    1.500000 kg")
        assert r is not None
        assert r.unit == "kg"

    # ── Potwierdzenia komend ──────────────────────────────────────────────

    def test_ack_A(self, proto):
        r = proto.parse_response("A")
        assert r is not None
        assert r.status == WeightStatus.STABLE

    def test_ack_tare(self, proto):
        r = proto.parse_response("T A")
        assert r is not None
        assert r.status == WeightStatus.STABLE

    def test_ack_zero(self, proto):
        r = proto.parse_response("Z A")
        assert r is not None
        assert r.status == WeightStatus.STABLE

    # ── Błędy i zakresy ───────────────────────────────────────────────────

    def test_over_range_OL(self, proto):
        r = proto.parse_response("OL")
        assert r is not None
        assert r.status == WeightStatus.OVER_RANGE

    def test_error_E(self, proto):
        r = proto.parse_response("E")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    def test_error_ES(self, proto):
        r = proto.parse_response("ES")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    def test_error_ERR(self, proto):
        r = proto.parse_response("ERR")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    # ── Nierozpoznane ─────────────────────────────────────────────────────

    def test_empty_line(self, proto):
        assert proto.parse_response("") is None

    def test_unknown_format(self, proto):
        assert proto.parse_response("HELLO WORLD") is None
