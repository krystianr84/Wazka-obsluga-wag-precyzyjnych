import pytest
from models.weight_reading import WeightStatus
from protocols.radwag_cbcp03_protocol import RadwagCbcp03Protocol


@pytest.fixture
def proto():
    return RadwagCbcp03Protocol()


class TestCbcp03Properties:
    def test_name(self, proto):
        assert proto.name == "Radwag CBCP-03"

    def test_baud_rate(self, proto):
        assert proto.default_baud_rate == 9600

    def test_commands_bytes(self, proto):
        assert proto.weight_command == b"S\r\n"
        assert proto.weight_immediate_command == b"SUI\r\n"
        assert proto.tare_command == b"T\r\n"
        assert proto.zero_command == b"Z\r\n"

    def test_command_list_not_empty(self, proto):
        assert len(proto.command_list) > 0


class TestCbcp03Parse:
    # ── Ramki masy — prefiks S ─────────────────────────────────────────────

    def test_stable_with_S_prefix(self, proto):
        r = proto.parse_response("S    50.000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(50.0)
        assert r.unit == "g"

    def test_stable_zero_with_S_prefix(self, proto):
        r = proto.parse_response("S     0.000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(0.0)

    # ── Ramki masy — prefiks SUI ───────────────────────────────────────────

    def test_dynamic_with_SUI_prefix(self, proto):
        r = proto.parse_response("SUI?  -   58.237 kg")
        assert r is not None
        assert r.status == WeightStatus.DYNAMIC
        assert r.value == pytest.approx(-58.237)
        assert r.unit == "kg"

    def test_stable_with_SUI_prefix(self, proto):
        r = proto.parse_response("SUI   172.000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(172.0)

    # ── Ramki masy — printout (bez prefiksu) ──────────────────────────────

    def test_printout_stable(self, proto):
        r = proto.parse_response("   50.000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(50.0)

    def test_printout_negative(self, proto):
        r = proto.parse_response("  -  1.500 kg")
        assert r is not None
        assert r.value == pytest.approx(-1.5)

    # ── Znak stabilności ──────────────────────────────────────────────────

    def test_over_range_stability_char(self, proto):
        r = proto.parse_response("S ^  172.000 g")
        assert r is not None
        assert r.status == WeightStatus.OVER_RANGE

    def test_under_range_stability_char(self, proto):
        r = proto.parse_response("S v    0.000 g")
        assert r is not None
        assert r.status == WeightStatus.UNDER_RANGE

    def test_comma_decimal(self, proto):
        r = proto.parse_response("S    50,000 g")
        assert r is not None
        assert r.value == pytest.approx(50.0)

    # ── Odpowiedzi statusowe — powodzenie ─────────────────────────────────

    def test_tare_done(self, proto):
        r = proto.parse_response("T D")
        assert r is not None
        assert r.status == WeightStatus.STABLE

    def test_zero_done(self, proto):
        r = proto.parse_response("Z D")
        assert r is not None
        assert r.status == WeightStatus.STABLE

    def test_command_ok(self, proto):
        r = proto.parse_response("DH OK")
        assert r is not None
        assert r.status == WeightStatus.STABLE

    # ── Odpowiedzi statusowe — w toku ─────────────────────────────────────

    def test_command_accepted(self, proto):
        r = proto.parse_response("S A")
        assert r is not None
        assert r.status == WeightStatus.IN_PROGRESS

    def test_tare_accepted(self, proto):
        r = proto.parse_response("T A")
        assert r is not None
        assert r.status == WeightStatus.IN_PROGRESS

    def test_command_impossible(self, proto):
        r = proto.parse_response("S I")
        assert r is not None
        assert r.status == WeightStatus.IN_PROGRESS

    # ── Błędy ─────────────────────────────────────────────────────────────

    def test_command_error_timeout(self, proto):
        r = proto.parse_response("T E")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    def test_unknown_command_ES(self, proto):
        r = proto.parse_response("ES")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    def test_error_prefix_ER(self, proto):
        r = proto.parse_response("ER")
        assert r is not None
        assert r.status == WeightStatus.ERROR

    # ── Zakresy ───────────────────────────────────────────────────────────

    def test_OL_over_range(self, proto):
        r = proto.parse_response("OL")
        assert r is not None
        assert r.status == WeightStatus.OVER_RANGE

    def test_LO_under_range(self, proto):
        r = proto.parse_response("LO")
        assert r is not None
        assert r.status == WeightStatus.UNDER_RANGE

    def test_command_over_range(self, proto):
        r = proto.parse_response("Z ^")
        assert r is not None
        assert r.status == WeightStatus.OVER_RANGE

    def test_command_under_range(self, proto):
        r = proto.parse_response("T v")
        assert r is not None
        assert r.status == WeightStatus.UNDER_RANGE

    # ── Nierozpoznane ─────────────────────────────────────────────────────

    def test_empty_line(self, proto):
        assert proto.parse_response("") is None

    def test_unknown_format(self, proto):
        assert proto.parse_response("BLABLA") is None
