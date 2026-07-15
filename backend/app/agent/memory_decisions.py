"""Agent memory decision rules — when to read, inject, or write long-term memory.

Rules for saving to long-term memory (only these trigger a write):
1. **Explicit remember** — user says "记住", "帮我记", "保存", "remember"
2. **Stable preference** — after-sales preference detected (refund method, comms channel)
   with at least 2 confirming signals in the conversation
3. **Multi-confirmed** — same preference stated 2+ times across turns
4. **Case summary** — a ticket was resolved (APPROVED/COMPLETED/REJECTED) and
   the result should be remembered for future reference

NOT saved:
- One-off inquiries (logistics tracking, order status)
- Temporary state (current session context)
- Casual chat / greetings
"""

from __future__ import annotations

import re

# ── Explicit "remember" trigger patterns ──────────────────────────────────

_EXPLICIT_REMEMBER_PATTERNS = [
    re.compile(r"记住[：:\s]*", re.IGNORECASE),
    re.compile(r"帮我记(?:一下|[下住])[：:\s]*", re.IGNORECASE),
    re.compile(r"保存[：:\s]*", re.IGNORECASE),
    re.compile(r"记住我", re.IGNORECASE),
    re.compile(r"别忘了", re.IGNORECASE),
    re.compile(r"remember\b", re.IGNORECASE),
    re.compile(r"save\s+this", re.IGNORECASE),
]

# ── After-sales preference keywords ──────────────────────────────────────

_PREFERENCE_KEYWORDS = [
    "退款到", "退款方式", "退款账户",
    "补发到", "补发地址", "换货地址",
    "微信联系", "电话联系", "短信通知", "邮件通知",
    "支付宝", "银行卡", "微信支付",
    "下次", "以后", "每次", "一直",
]

# ── Ticket resolution keywords ───────────────────────────────────────────

_RESOLUTION_KEYWORDS = [
    "已通过", "已审核", "已退款", "已补发",
    "已拒绝", "已完成", "已关闭",
    "approved", "completed", "rejected", "resolved",
]


def should_save_memory(
    user_message: str,
    response_text: str | None,
    intent: str | None,
    tool_results: list[dict] | None,
    turn_count: int,
) -> tuple[bool, str | None, str | None]:
    """Determine whether the current turn should trigger a memory write.

    Returns
    -------
    (should_save, memory_type, extracted_content)
        - ``should_save``: whether to write memory
        - ``memory_type``: ``"FACT"``, ``"PREFERENCE"``, or ``"SUMMARY"``
        - ``extracted_content``: the content to save, or ``None``
    """
    # ── Rule 1: Explicit "remember" ──────────────────────────────────
    for pattern in _EXPLICIT_REMEMBER_PATTERNS:
        m = pattern.search(user_message)
        if m:
            # Extract what comes after the trigger
            content = user_message[m.end():].strip()
            if content:
                return True, "FACT", content
            return True, "FACT", user_message

    # ── Rule 2: Stable after-sales preference ────────────────────────
    pref_hits = sum(
        1 for kw in _PREFERENCE_KEYWORDS if kw in user_message
    )
    if pref_hits >= 2 and turn_count >= 2:
        return True, "PREFERENCE", _extract_preference(user_message)

    # ── Rule 3: Multi-turn confirmed preference ──────────────────────
    if pref_hits >= 1 and turn_count >= 3:
        return True, "PREFERENCE", _extract_preference(user_message)

    # ── Rule 4: Ticket resolution summary ────────────────────────────
    has_resolution = _check_ticket_resolution(response_text, tool_results)
    if has_resolution:
        return True, "SUMMARY", _extract_summary(response_text, tool_results)

    return False, None, None


def should_not_save(user_message: str) -> bool:
    """Return True if this is a one-off inquiry that should NOT be remembered.

    Covers: logistics tracking, order status checks, greetings, single questions.
    """
    # One-off patterns
    one_off_patterns = [
        r"(?:查|看|跟踪|查询).*(?:物流|快递|到哪|在哪)",
        r"(?:订单|快递).*(?:状态|进度|到哪)",
        r"^(?:你好|您好|hi|hello|在吗|在不在)[\s!！。.,，]*$",
        r"^(?:谢谢|感谢|好的|OK|ok|嗯|哦)[\s!！。.,，]*$",
        r"(?:什么时候|几点|多久|多长时间)",
        r"(?:能|可以|可不可以|能不能).{0,10}(?:吗|么|不)",
    ]
    return any(
        re.search(pattern, user_message, re.IGNORECASE)
        for pattern in one_off_patterns
    )


def _extract_preference(text: str) -> str:
    """Extract a preference summary from user text."""
    for kw in _PREFERENCE_KEYWORDS:
        if kw in text:
            idx = text.index(kw)
            start = max(0, idx - 20)
            end = min(len(text), idx + len(kw) + 30)
            snippet = text[start:end].strip()
            return snippet
    return text[:200]


def _extract_summary(response_text: str | None, tool_results: list[dict] | None) -> str:
    """Extract a ticket resolution summary."""
    parts: list[str] = []
    if tool_results:
        for tr in tool_results:
            if not tr.get("is_success"):
                continue
            data = tr.get("data") or tr.get("raw_data") or {}
            ticket_num = data.get("ticket_number", "")
            status = data.get("status", "")
            if ticket_num or status:
                parts.append(f"工单 {ticket_num} 状态: {status}")
    if not parts:
        parts.append(response_text[:300] if response_text else "")
    return "。".join(parts)


def _check_ticket_resolution(
    response_text: str | None, tool_results: list[dict] | None,
) -> bool:
    """Check whether a ticket was resolved in this turn."""
    # Check tool results
    if tool_results:
        for tr in tool_results:
            if not tr.get("is_success"):
                continue
            tool_name = tr.get("tool_name", "")
            if tool_name not in (
                "create_after_sales_ticket", "cancel_after_sales_ticket",
            ):
                continue
            data = tr.get("data") or tr.get("raw_data") or {}
            status = data.get("status", "")
            if status in ("APPROVED", "REJECTED", "COMPLETED"):
                return True

    # Check response text
    if response_text:
        for kw in _RESOLUTION_KEYWORDS:
            if kw in response_text:
                return True

    return False
