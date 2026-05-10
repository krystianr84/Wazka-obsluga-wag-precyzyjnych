import pytest
from models.weight_reading import WeightStatus
from services.scale_service import _fallback_parse


class TestFallbackParse:
    # ── Poprawne formaty ──────────────────────────────────────────────────

    def test_compact_comma_no_space(self):
        r = _fallback_parse("0,000g")
        assert r is not None
        assert r.status == WeightStatus.STABLE
        assert r.value == pytest.approx(0.0)
        assert r.unit == "g"

    def test_compact_dot_with_space(self):
        r = _fallback_parse("50.000 g")
        assert r is not None
        assert r.value == pytest.approx(50.0)
        assert r.unit == "g"

    def test_negative_with_comma(self):
        r = _fallback_parse("-1,234kg")
        assert r is not None
        assert r.value == pytest.approx(-1.234)
        assert r.unit == "kg"

    def test_positive_sign_explicit(self):
        r = _fallback_parse("+50.000 g")
        assert r is not None
        assert r.value == pytest.approx(50.0)

    def test_kilogram(self):
        r = _fallback_parse("1.500 kg")
        assert r is not None
        assert r.unit == "kg"
        assert r.value == pytest.approx(1.5)

    def test_compound_unit(self):
        r = _fallback_parse("9.810 N/g")
        assert r is not None
        assert r.unit == "N/g"

    def test_always_stable_status(self):
        r = _fallback_parse("10.000 g")
        assert r is not None
        assert r.status == WeightStatus.STABLE

    # ── Niepoprawne formaty ────────────────────────────────────────────────

    def test_empty(self):
        assert _fallback_parse("") is None

    def test_no_unit(self):
        assert _fallback_parse("50.000") is None

    def test_no_decimal(self):
        assert _fallback_parse("50 g") is None

    def test_plain_text(self):
        assert _fallback_parse("S S 50.000 g") is None

    def test_status_prefix(self):
        assert _fallback_parse("ST,GS,+   50.000000 g") is None
