"""Unit tests for memory privacy filter — sensitive info detection."""


from app.services.memory_privacy import (
    contains_sensitive_info,
    sanitize_memory_content,
)


class TestContainsSensitiveInfo:
    def test_clean_text_returns_none(self) -> None:
        assert contains_sensitive_info("用户喜欢通过微信联系客服") is None
        assert contains_sensitive_info("偏好退款到支付宝账户") is None
        assert contains_sensitive_info("Remember to follow up on ticket #123") is None

    def test_detects_jwt_token(self) -> None:
        reason = contains_sensitive_info(
            "token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNjpGGVXX0sDnA"
        )
        assert reason is not None
        assert "JWT" in reason

    def test_detects_bank_card_unionpay(self) -> None:
        reason = contains_sensitive_info("银行卡号 6222021234567890123")
        assert reason is not None
        assert "银行卡" in reason

    def test_detects_bank_card_visa(self) -> None:
        reason = contains_sensitive_info("card: 4111111111111111")
        assert reason is not None
        assert "银行卡" in reason

    def test_detects_cn_id_number(self) -> None:
        reason = contains_sensitive_info("身份证 110101199001011234")
        assert reason is not None
        assert "身份证" in reason

    def test_detects_api_key(self) -> None:
        reason = contains_sensitive_info("api key: sk-abc123def456ghi789jkl012mno345pqr678stu")
        assert reason is not None
        assert "API Key" in reason

    def test_detects_password(self) -> None:
        reason = contains_sensitive_info("password: mySecret123")
        assert reason is not None
        assert "密码" in reason

    def test_detects_detailed_address(self) -> None:
        reason = contains_sensitive_info("地址：北京市朝阳区某某街道某某路123号")
        assert reason is not None
        assert "地址" in reason

    def test_normal_address_context_is_ok(self) -> None:
        # "北京市" alone without detailed street/road info should be OK
        assert contains_sensitive_info("我在北京") is None


class TestSanitizeMemoryContent:
    def test_clean_content_returns_none(self) -> None:
        assert sanitize_memory_content("用户偏好微信沟通", None) is None

    def test_sensitive_content_returns_reason(self) -> None:
        reason = sanitize_memory_content("password: abc123", None)
        assert reason is not None

    def test_sensitive_in_structured_data(self) -> None:
        reason = sanitize_memory_content(
            "偏好设置",
            {"card_number": "6222021234567890123"},
        )
        assert reason is not None
        assert "银行卡" in reason

    def test_clean_structured_data(self) -> None:
        assert sanitize_memory_content(
            "偏好设置",
            {"preferred_channel": "wechat", "preferred_language": "zh"},
        ) is None

    def test_empty_content(self) -> None:
        assert sanitize_memory_content("", None) is None
