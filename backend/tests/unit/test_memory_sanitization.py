"""Unit tests for memory data minimization (LLM field projection)."""


from app.agent.sanitization import MEMORY_LLM_FIELDS, project_memory_for_llm


class TestProjectMemoryForLLM:
    def test_only_allowed_fields_present(self) -> None:
        raw = {
            "id": "abc-123",
            "user_id": "user-456",
            "memory_type": "PREFERENCE",
            "key": "refund_method",
            "content": "用户偏好支付宝退款",
            "structured_data": {"channel": "alipay"},
            "source": "agent_inferred",
            "confidence": 0.9,
            "status": "ACTIVE",
            "version": 2,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
        }
        projected = project_memory_for_llm(raw)
        assert "memory_type" in projected
        assert "key" in projected
        assert "content" in projected
        assert "confidence" in projected

        # Must NOT contain internal fields
        assert "id" not in projected
        assert "user_id" not in projected
        assert "status" not in projected
        assert "version" not in projected
        assert "source" not in projected
        assert "created_at" not in projected
        assert "updated_at" not in projected
        assert "structured_data" not in projected

    def test_fields_match_allowlist(self) -> None:
        assert "memory_type" in MEMORY_LLM_FIELDS
        assert "key" in MEMORY_LLM_FIELDS
        assert "content" in MEMORY_LLM_FIELDS
        assert "confidence" in MEMORY_LLM_FIELDS
        assert len(MEMORY_LLM_FIELDS) == 4

    def test_empty_dict(self) -> None:
        result = project_memory_for_llm({})
        assert result == {}

    def test_missing_fields_are_excluded(self) -> None:
        raw = {"content": "test", "extra_field": "should be removed"}
        projected = project_memory_for_llm(raw)
        assert projected == {"content": "test"}
