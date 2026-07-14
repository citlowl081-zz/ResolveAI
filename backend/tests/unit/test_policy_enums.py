"""Unit tests for PolicyCategory and PolicyStatus enums."""

import pytest

from app.models.enums import PolicyCategory, PolicyStatus


class TestPolicyCategory:
    """PolicyCategory enum — values and from_prefix()."""

    def test_all_expected_values(self) -> None:
        expected = {
            "RETURN", "REFUND", "EXCHANGE", "RESHIPMENT",
            "LOGISTICS", "RISK", "SOP", "GENERAL",
        }
        assert {c.value for c in PolicyCategory} == expected

    def test_from_prefix_known(self) -> None:
        assert PolicyCategory.from_prefix("RET") is PolicyCategory.RETURN
        assert PolicyCategory.from_prefix("REF") is PolicyCategory.REFUND
        assert PolicyCategory.from_prefix("EXC") is PolicyCategory.EXCHANGE
        assert PolicyCategory.from_prefix("RES") is PolicyCategory.RESHIPMENT
        assert PolicyCategory.from_prefix("LOG") is PolicyCategory.LOGISTICS
        assert PolicyCategory.from_prefix("RISK") is PolicyCategory.RISK
        assert PolicyCategory.from_prefix("SOP") is PolicyCategory.SOP
        assert PolicyCategory.from_prefix("GEN") is PolicyCategory.GENERAL

    def test_from_prefix_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown policy_key prefix"):
            PolicyCategory.from_prefix("XYZ")


class TestPolicyStatus:
    """PolicyStatus enum — values."""

    def test_all_expected_values(self) -> None:
        expected = {"DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED"}
        assert {s.value for s in PolicyStatus} == expected
