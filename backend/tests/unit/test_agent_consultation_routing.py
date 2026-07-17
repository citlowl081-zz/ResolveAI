"""Regression tests for consultation-versus-action routing."""

from typing import Any, cast

import pytest

from app.agent.nodes.classify_intent import classify_intent
from app.agent.nodes.compose_response import compose_response
from app.agent.nodes.handle_tool_error import handle_tool_error
from app.agent.nodes.select_tools import select_tools
from app.agent.provider import set_provider
from app.agent.routing import (
    route_after_classify_intent,
    route_after_handle_tool_error,
)
from app.agent.state import AgentState
from app.llm.mock_provider import MockProvider
from app.llm.provider import ChatResponse, ModelProvider


def _state(message: str) -> AgentState:
    return cast(AgentState, {
        "user_message": message,
        "user_role": "CUSTOMER",
        "confirm_action_id": None,
        "context": {"orders": []},
        "node_timings": [],
        "errors": [],
        "tool_results": [],
        "intent": None,
        "request_mode": None,
        "injection_detected": False,
        "terminal_error": False,
        "context_messages": [],
    })


class _FailingProvider(ModelProvider):
    @property
    def provider_name(self) -> str:
        return "unknown"

    async def chat(self, request: Any) -> ChatResponse:
        raise RuntimeError("provider unavailable")

    async def chat_structured(
        self, request: Any, output_schema: dict[str, Any],
    ) -> ChatResponse:
        raise RuntimeError("provider unavailable")


class _StructuredFallbackProvider(ModelProvider):
    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    async def chat(self, request: Any) -> ChatResponse:
        raise AssertionError("chat() should not be used for intent classification")

    async def chat_structured(
        self, request: Any, output_schema: dict[str, Any],
    ) -> ChatResponse:
        return ChatResponse(
            content=(
                '{"intent":"PRE_SHIP_REFUND","confidence":0.9,'
                '"request_mode":"CONSULTATION"}'
            ),
            model="qwen-test",
            metadata={
                "structured_output_failed": True,
                "fallback_used": True,
                "fallback_reason": "json_schema_unsupported",
            },
        )


class _PostDeliveryRefundProvider(ModelProvider):
    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    async def chat(self, request: Any) -> ChatResponse:
        raise AssertionError("chat() should not be used for intent classification")

    async def chat_structured(
        self, request: Any, output_schema: dict[str, Any],
    ) -> ChatResponse:
        return ChatResponse(
            content=(
                '{"intent":"PRE_SHIP_REFUND","confidence":0.95,'
                '"request_mode":"ACTION"}'
            ),
            model="qwen-test",
        )


@pytest.mark.parametrize("message", [
    "能退吗",
    "是否可以退款",
    "拆封后还能退吗",
    "七天无理由是什么",
    "换货政策是什么",
    "退款需要什么条件",
    "我想了解退货流程",
])
async def test_consultation_routes_only_to_policy_search(message: str) -> None:
    set_provider(_FailingProvider())
    state = await classify_intent(_state(message))
    state = await select_tools(state)

    assert state["request_mode"] == "CONSULTATION"
    assert state["planned_tools"] == [{
        "tool_name": "search_after_sales_policy",
        "tool_input": {"query": message, "top_k": 5},
    }]


@pytest.mark.parametrize("message", [
    "帮我申请退款",
    "现在给我退掉",
    "帮我创建退货申请",
    "我要提交换货",
    "请给我补发",
])
async def test_explicit_action_is_classified_as_action(message: str) -> None:
    set_provider(_FailingProvider())
    state = await classify_intent(_state(message))
    assert state["request_mode"] == "ACTION"


async def test_model_failure_cannot_upgrade_policy_question_to_write_action() -> None:
    message = "我买的耳机拆封试用后不合适，还可以七天无理由退货吗？"
    state = _state(message)
    state["context"] = {
        "orders": [{
            "id": "order-id",
            "items": [{
                "id": "item-id", "product_id": "product-id",
                "product_name": "Wireless Headphones", "quantity": 1,
                "refunded_quantity": 0, "reshipped_quantity": 0,
            }],
        }],
    }
    set_provider(_FailingProvider())

    state = await classify_intent(state)
    state = await select_tools(state)
    state = await compose_response(state)

    assert state["request_mode"] == "CONSULTATION"
    assert state.get("proposed_actions") == []
    assert state.get("_pending_action_for_snapshot") is None
    classify_trace = next(
        timing for timing in state["node_timings"]
        if timing["node"] == "classify_intent"
    )
    assert classify_trace["llm_call"]["provider"] == "unknown"
    assert classify_trace["llm_call"]["real_llm_success"] is False
    assert classify_trace["llm_call"]["structured_output_failed"] is True
    assert classify_trace["llm_call"]["fallback_used"] is True
    assert classify_trace["llm_call"]["fallback_reason"] == "RuntimeError"


async def test_trace_records_provider_structured_output_fallback() -> None:
    set_provider(_StructuredFallbackProvider())

    state = await classify_intent(_state("拆封耳机还能退吗？"))

    trace = state["node_timings"][0]["llm_call"]
    assert trace["provider"] == "openai_compatible"
    assert trace["real_llm_success"] is True
    assert trace["structured_output_failed"] is True
    assert trace["fallback_used"] is True
    assert trace["fallback_reason"] == "json_schema_unsupported"


async def test_llm_action_proposal_is_ignored_for_consultation() -> None:
    state = _state("拆封耳机还能退吗？")
    state["request_mode"] = "CONSULTATION"
    state["intent"] = "PRE_SHIP_REFUND"
    state["context"] = {
        "orders": [{
            "id": "order-id",
            "items": [{
                "id": "item-id", "product_id": "product-id",
                "product_name": "Wireless Headphones", "quantity": 1,
                "refunded_quantity": 0, "reshipped_quantity": 0,
            }],
        }],
    }
    set_provider(MockProvider(responses=[ChatResponse(
        content=(
            '{"response":"可以退","propose_action":{"intent":"PRE_SHIP_REFUND",'
            '"items":[{"product_name":"Wireless Headphones","quantity":1,'
            '"reason_code":"OTHER"}],"description":"创建退款工单"}}'
        ),
        model="mock",
    )]))

    result = await compose_response(state)

    assert result.get("proposed_actions") == []
    assert result.get("_pending_action_for_snapshot") is None


async def test_llm_action_proposal_is_persisted_for_confirmation() -> None:
    state = _state("请帮我创建耳机退款申请")
    state["request_mode"] = "ACTION"
    state["intent"] = "PRE_SHIP_REFUND"
    state["context"] = {
        "orders": [{
            "id": "order-id",
            "items": [{
                "id": "item-id", "product_id": "product-id",
                "product_name": "Wireless Headphones", "quantity": 1,
                "refunded_quantity": 0, "reshipped_quantity": 0,
            }],
        }],
    }
    state["_pending_action_for_snapshot"] = None
    set_provider(MockProvider(responses=[ChatResponse(
        content=(
            '{"response":"请确认退款申请","propose_action":'
            '{"intent":"PRE_SHIP_REFUND","items":'
            '[{"product_name":"Wireless Headphones","quantity":1,'
            '"reason_code":"OTHER"}],"description":"创建退款工单"}}'
        ),
        model="mock",
    )]))

    result = await compose_response(state)

    proposed_actions = result.get("proposed_actions")
    assert proposed_actions is not None
    assert len(proposed_actions) == 1
    pending = result.get("_pending_action_for_snapshot")
    assert pending is not None
    assert pending["action_id"] == proposed_actions[0]["action_id"]


async def test_blank_llm_action_description_gets_safe_default() -> None:
    state = _state("请帮我创建耳机退款申请")
    state["request_mode"] = "ACTION"
    state["intent"] = "QUALITY_REFUND"
    state["context"] = {
        "orders": [{
            "id": "order-id",
            "items": [{
                "id": "item-id", "product_id": "product-id",
                "product_name": "Wireless Headphones", "quantity": 1,
                "refunded_quantity": 0, "reshipped_quantity": 0,
            }],
        }],
    }
    set_provider(MockProvider(responses=[ChatResponse(
        content=(
            '{"response":"请确认退款申请","propose_action":'
            '{"intent":"QUALITY_REFUND","items":'
            '[{"product_name":"Wireless Headphones","quantity":1,'
            '"reason_code":"OTHER"}],"description":""}}'
        ),
        model="mock",
    )]))

    result = await compose_response(state)

    proposed = result.get("proposed_actions")
    assert proposed is not None
    assert proposed[0]["description"] == "为您创建QUALITY_REFUND工单"


async def test_explicit_headphone_action_selects_matching_order() -> None:
    state = _state("请帮我创建耳机退款申请")
    state["request_mode"] = "ACTION"
    state["context"] = {
        "orders": [
            {"id": "shoes", "items": [{"product_name": "Running Shoes"}]},
            {"id": "headphones", "items": [{"product_name": "Wireless Headphones"}]},
        ]
    }

    result = await select_tools(state)

    planned = result["planned_tools"]
    assert planned is not None
    assert planned[0]["tool_input"]["order_id"] == "headphones"


async def test_delivered_order_action_is_not_proposed_as_pre_ship_refund() -> None:
    state = _state("我确认要退这个耳机，请帮我创建退款申请。")
    state["context"] = {
        "orders": [{
            "id": "headphones",
            "status": "DELIVERED",
            "items": [{"product_name": "Wireless Headphones"}],
        }],
    }
    set_provider(_PostDeliveryRefundProvider())

    result = await classify_intent(state)

    assert result["request_mode"] == "ACTION"
    assert result["intent"] == "QUALITY_REFUND"


async def test_explicit_action_gets_safe_proposal_when_model_returns_null() -> None:
    state = _state("我确定要退这个耳机，请帮我创建退款申请。")
    state["request_mode"] = "ACTION"
    state["intent"] = "PRE_SHIP_REFUND"
    order = {
        "id": "order-id",
        "items": [{
            "id": "item-id", "product_id": "product-id",
            "product_name": "Wireless Headphones", "quantity": 1,
            "refunded_quantity": 0, "reshipped_quantity": 0,
        }],
    }
    state["context"] = {"orders": [order]}
    state["tool_results"] = [{
        "tool_name": "get_order", "is_success": True, "raw_data": order,
    }]
    set_provider(MockProvider(responses=[ChatResponse(
        content='{"response":"好的，请确认操作。","propose_action":null}',
        model="mock",
    )]))

    result = await compose_response(state)

    proposed = result.get("proposed_actions")
    assert proposed is not None
    assert len(proposed) == 1
    assert proposed[0]["status"] == "pending_confirmation"


async def test_non_retryable_tool_error_routes_to_response() -> None:
    state = _state("查询物流")
    state["tool_results"] = [{
        "tool_name": "get_logistics",
        "is_success": False,
        "error_code": "NOT_FOUND",
        "error_message": "未找到物流信息",
    }]

    result = await handle_tool_error(state)

    assert result["retry_tool_execution"] is False
    assert route_after_handle_tool_error(result) == "compose_response"


async def test_retryable_tool_error_routes_to_retry() -> None:
    state = _state("查询物流")
    state["max_loops"] = 3
    state["tool_results"] = [{
        "tool_name": "get_logistics",
        "is_success": False,
        "error_code": "TOOL_TIMEOUT",
        "error_message": "工具调用超时",
    }]

    result = await handle_tool_error(state)

    assert result["retry_tool_execution"] is True
    assert route_after_handle_tool_error(result) == "execute_tool"


def test_valid_confirmation_routes_to_tool_despite_low_llm_confidence() -> None:
    state = _state("确认执行")
    state["confidence"] = 0.1
    state["pending_action_valid"] = True

    assert route_after_classify_intent(state) == "select_tools"


async def test_policy_fallback_prefers_meaningful_summary_over_heading() -> None:
    state = _state("耳机拆封后还能退吗？")
    state["request_mode"] = "CONSULTATION"
    state["intent"] = "OTHER"
    state["tool_results"] = [{
        "tool_name": "search_after_sales_policy",
        "is_success": True,
        "data": {"policies": [{
            "policy_key": "POL-RET-901",
            "title": "网络购物七日无理由退货规则",
            "source": "legal_requirement",
            "snippet": "# 七日无理由退货规则",
            "content_summary": "合理试用且商品保持完好的，可依法申请退货。",
        }]},
    }]
    set_provider(_FailingProvider())

    result = await compose_response(state)

    response_text = result["response_text"]
    assert response_text is not None
    assert "合理试用且商品保持完好" in response_text
