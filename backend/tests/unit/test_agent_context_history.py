"""Short-term context must contain prior visible turns only."""

import uuid

from app.agent.nodes.build_context import _project_prior_messages
from app.agent.nodes.select_tools import _contextual_policy_query
from app.models.agent_message import AgentMessage


def _message(role: str, content: str, sequence: int) -> AgentMessage:
    return AgentMessage(
        session_id=uuid.uuid4(), turn_id=uuid.uuid4(), role=role,
        content=content, sequence_number=sequence, turn_sequence=sequence,
    )


def test_current_user_message_is_not_duplicated_in_context() -> None:
    messages = [
        _message("USER", "我买的是 Aurora Buds Pro。", 1),
        _message("ASSISTANT", "好的。", 2),
        _message("TOOL", "internal", 3),
        _message("USER", "它拆封后还能退吗？", 4),
    ]

    projected = _project_prior_messages(messages, current_sequence=4)

    assert [item["content"] for item in projected] == [
        "我买的是 Aurora Buds Pro。", "好的。",
    ]


def test_policy_follow_up_includes_previous_product_reference() -> None:
    state = {
        "user_message": "它拆封试用后还能退吗？",
        "context_messages": [
            {"role": "USER", "content": "我买的是 Aurora Buds Pro。"},
            {"role": "ASSISTANT", "content": "请问需要了解什么？"},
        ],
    }

    query = _contextual_policy_query(state)  # type: ignore[arg-type]

    assert "Aurora Buds Pro" in query
    assert "拆封试用" in query
