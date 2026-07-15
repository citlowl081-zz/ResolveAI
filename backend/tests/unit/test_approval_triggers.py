"""Unit tests for approval trigger rules."""

from decimal import Decimal

from app.rules.approval_triggers import check_approval_required


class TestCheckApprovalRequired:
    def test_no_triggers_low_risk_single_item(self) -> None:
        triggers = check_approval_required(
            intent="QUALITY_REFUND",
            estimated_refund=Decimal("50"),
            high_refund_threshold=Decimal("1000"),
            risk_level="LOW",
            item_count=1,
        )
        assert triggers == []

    def test_high_refund_triggers(self) -> None:
        triggers = check_approval_required(
            intent="QUALITY_REFUND",
            estimated_refund=Decimal("2000"),
            high_refund_threshold=Decimal("1000"),
            risk_level="LOW",
            item_count=1,
        )
        assert "HIGH_REFUND" in triggers

    def test_high_risk_triggers(self) -> None:
        triggers = check_approval_required(
            intent="QUALITY_REFUND",
            estimated_refund=Decimal("50"),
            high_refund_threshold=Decimal("1000"),
            risk_level="HIGH",
            item_count=1,
        )
        assert "RISK_HIT" in triggers

    def test_exchange_triggers(self) -> None:
        triggers = check_approval_required(
            intent="EXCHANGE",
            estimated_refund=Decimal("50"),
            high_refund_threshold=Decimal("1000"),
            risk_level="LOW",
            item_count=1,
        )
        assert "EXCHANGE" in triggers

    def test_multi_item_triggers(self) -> None:
        triggers = check_approval_required(
            intent="QUALITY_REFUND",
            estimated_refund=Decimal("50"),
            high_refund_threshold=Decimal("1000"),
            risk_level="LOW",
            item_count=3,
        )
        assert "MULTI_ITEM" in triggers

    def test_all_triggers_at_once(self) -> None:
        triggers = check_approval_required(
            intent="EXCHANGE",
            estimated_refund=Decimal("5000"),
            high_refund_threshold=Decimal("1000"),
            risk_level="HIGH",
            item_count=5,
        )
        assert "HIGH_REFUND" in triggers
        assert "RISK_HIT" in triggers
        assert "EXCHANGE" in triggers
        assert "MULTI_ITEM" in triggers
        assert len(triggers) == 4

    def test_exact_threshold_no_trigger(self) -> None:
        triggers = check_approval_required(
            intent="QUALITY_REFUND",
            estimated_refund=Decimal("1000.00"),
            high_refund_threshold=Decimal("1000.00"),
            risk_level="LOW",
            item_count=1,
        )
        # Exact threshold does NOT trigger (must exceed)
        assert "HIGH_REFUND" not in triggers

    def test_one_cent_over_triggers(self) -> None:
        triggers = check_approval_required(
            intent="QUALITY_REFUND",
            estimated_refund=Decimal("1000.01"),
            high_refund_threshold=Decimal("1000.00"),
            risk_level="LOW",
            item_count=1,
        )
        assert "HIGH_REFUND" in triggers
