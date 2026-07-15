"""Unit tests for ApprovalStatus and ApprovalType enums."""


from app.models.enums import ApprovalStatus, ApprovalType


class TestApprovalStatus:
    def test_all_values(self) -> None:
        assert ApprovalStatus.PENDING.value == "PENDING"
        assert ApprovalStatus.APPROVED.value == "APPROVED"
        assert ApprovalStatus.REJECTED.value == "REJECTED"
        assert ApprovalStatus.EXPIRED.value == "EXPIRED"
        assert ApprovalStatus.CANCELLED.value == "CANCELLED"

    def test_membership(self) -> None:
        assert "PENDING" in ApprovalStatus.__members__
        assert "INVALID" not in ApprovalStatus.__members__


class TestApprovalType:
    def test_all_values(self) -> None:
        assert ApprovalType.HIGH_REFUND.value == "HIGH_REFUND"
        assert ApprovalType.RISK_HIT.value == "RISK_HIT"
        assert ApprovalType.EXCHANGE.value == "EXCHANGE"
        assert ApprovalType.MULTI_ITEM.value == "MULTI_ITEM"
        assert ApprovalType.MANUAL_REQUEST.value == "MANUAL_REQUEST"

    def test_membership(self) -> None:
        assert "HIGH_REFUND" in ApprovalType.__members__
        assert "INVALID" not in ApprovalType.__members__
