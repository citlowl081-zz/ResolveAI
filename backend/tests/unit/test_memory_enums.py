"""Unit tests for MemoryType and MemoryStatus enums."""

import pytest

from app.models.enums import MemoryStatus, MemoryType


class TestMemoryType:
    def test_all_values_present(self) -> None:
        assert MemoryType.PREFERENCE.value == "PREFERENCE"
        assert MemoryType.FACT.value == "FACT"
        assert MemoryType.SUMMARY.value == "SUMMARY"
        assert MemoryType.COMMITMENT.value == "COMMITMENT"
        assert MemoryType.RISK_PROFILE.value == "RISK_PROFILE"

    def test_membership_check(self) -> None:
        assert "PREFERENCE" in MemoryType.__members__
        assert "FACT" in MemoryType.__members__
        assert "INVALID" not in MemoryType.__members__

    def test_construct_from_string(self) -> None:
        assert MemoryType("PREFERENCE") == MemoryType.PREFERENCE
        assert MemoryType("FACT") == MemoryType.FACT

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            MemoryType("INVALID_TYPE")


class TestMemoryStatus:
    def test_all_values_present(self) -> None:
        assert MemoryStatus.ACTIVE.value == "ACTIVE"
        assert MemoryStatus.ARCHIVED.value == "ARCHIVED"
        assert MemoryStatus.SUPERSEDED.value == "SUPERSEDED"

    def test_membership_check(self) -> None:
        assert "ACTIVE" in MemoryStatus.__members__
        assert "ARCHIVED" in MemoryStatus.__members__
        assert "INVALID" not in MemoryStatus.__members__

    def test_construct_from_string(self) -> None:
        assert MemoryStatus("ACTIVE") == MemoryStatus.ACTIVE
        assert MemoryStatus("ARCHIVED") == MemoryStatus.ARCHIVED
