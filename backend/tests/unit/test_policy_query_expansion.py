"""Deterministic retrieval hints for common after-sales wording gaps."""

from app.services.policy_service import _expand_policy_query


def test_missing_item_wording_expands_to_policy_terms() -> None:
    expanded = _expand_policy_query("少发商品怎么处理")

    for term in ("少件", "漏件", "错发", "补发"):
        assert term in expanded


def test_opened_headphones_expands_to_condition_terms() -> None:
    expanded = _expand_policy_query("耳机拆封试用后能退吗")

    for term in ("数码产品", "合理试用", "商品完好", "七日无理由"):
        assert term in expanded


def test_unrelated_query_is_unchanged() -> None:
    assert _expand_policy_query("你好") == "你好"
