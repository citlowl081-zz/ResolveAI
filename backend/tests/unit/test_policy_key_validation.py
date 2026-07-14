"""Unit tests for policy_key validation functions (no DB required)."""

import pytest

from app.models.enums import PolicyCategory
from app.rag.validation import (
    POLICY_KEY_PREFIXES,
    validate_policy_key,
    validate_policy_key_and_category,
)


class TestPolicyKeyPrefixes:
    def test_all_eight_prefixes(self) -> None:
        assert frozenset(
            {"RET", "REF", "EXC", "RES", "LOG", "RISK", "SOP", "GEN"}
        ) == POLICY_KEY_PREFIXES


class TestValidatePolicyKey:
    """Format validation only — no category check."""

    @pytest.mark.parametrize("key", [
        "POL-RET-001",
        "POL-REF-001",
        "POL-EXC-001",
        "POL-RES-001",
        "POL-LOG-001",
        "POL-RISK-001",
        "POL-SOP-001",
        "POL-GEN-001",
        "POL-REF-999",
        "POL-RET-000",
    ])
    def test_valid_keys(self, key: str) -> None:
        result = validate_policy_key(key)
        assert result == key.strip()

    @pytest.mark.parametrize("key,expected_msg_fragment", [
        ("", "non-empty"),
        ("   ", "non-empty"),
        ("POL-ABC-001", "Invalid policy_key"),
        ("POL-RET-12", "Invalid policy_key"),        # only 2 digits
        ("POL-RET-1234", "Invalid policy_key"),      # 4 digits
        ("pol-ref-001", "Invalid policy_key"),        # lowercase
        ("POL-REF-001-extra", "Invalid policy_key"),  # trailing
        ("REF-001", "Invalid policy_key"),             # missing POL-
        ("POL--REF-001", "Invalid policy_key"),        # double dash
        ("POL-REF-00X", "Invalid policy_key"),         # non-digit
        ("POL-XXX-001", "Invalid policy_key"),         # unknown prefix
    ])
    def test_invalid_keys(self, key: str, expected_msg_fragment: str) -> None:
        with pytest.raises(ValueError, match=expected_msg_fragment):
            validate_policy_key(key)


class TestValidatePolicyKeyAndCategory:
    """Format + prefix–category consistency."""

    def test_valid_key_with_enum_category(self) -> None:
        key, cat = validate_policy_key_and_category(
            "POL-REF-001", PolicyCategory.REFUND
        )
        assert key == "POL-REF-001"
        assert cat is PolicyCategory.REFUND

    def test_valid_key_with_string_category(self) -> None:
        key, cat = validate_policy_key_and_category("POL-RET-001", "RETURN")
        assert key == "POL-RET-001"
        assert cat is PolicyCategory.RETURN

    def test_each_prefix_matches_category(self) -> None:
        mapping = [
            ("POL-RET-001", PolicyCategory.RETURN),
            ("POL-REF-001", PolicyCategory.REFUND),
            ("POL-EXC-001", PolicyCategory.EXCHANGE),
            ("POL-RES-001", PolicyCategory.RESHIPMENT),
            ("POL-LOG-001", PolicyCategory.LOGISTICS),
            ("POL-RISK-001", PolicyCategory.RISK),
            ("POL-SOP-001", PolicyCategory.SOP),
            ("POL-GEN-001", PolicyCategory.GENERAL),
        ]
        for key, cat in mapping:
            _, result_cat = validate_policy_key_and_category(key, cat)
            assert result_cat is cat

    def test_prefix_category_mismatch(self) -> None:
        with pytest.raises(ValueError, match="maps to category"):
            validate_policy_key_and_category("POL-REF-001", PolicyCategory.RETURN)

    def test_unknown_string_category(self) -> None:
        with pytest.raises(ValueError, match="Unknown policy category"):
            validate_policy_key_and_category("POL-REF-001", "INVALID_CATEGORY")

    def test_bad_category_type(self) -> None:
        with pytest.raises(ValueError, match="must be a PolicyCategory or str"):
            validate_policy_key_and_category("POL-REF-001", 123)
