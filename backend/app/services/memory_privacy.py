"""Memory privacy filter — detects and rejects sensitive information before storage.

Protected data categories (must never be stored in long-term memory):
- Passwords / passphrases
- JWT / OAuth tokens
- API keys
- Full bank card / payment instrument numbers
- Full government ID numbers (Chinese ID, passport, etc.)
- Complete, precise home addresses
- Raw credential-like strings
"""

from __future__ import annotations

import re

# ── Detection patterns (coarse, conservative) ────────────────────────────

_JWT_PATTERN = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    re.IGNORECASE,
)

_BANK_CARD_PATTERN = re.compile(
    r"\b(?:62\d{14,17}|[35]\d{15}|4\d{15}(?:\d{3})?)\b"  # UnionPay / Amex / Visa
)

_CN_ID_PATTERN = re.compile(
    r"\b[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]\b"
)

_API_KEY_PATTERN = re.compile(
    r"\b(sk-[A-Za-z0-9]{20,}|[A-Za-z0-9]{32,64})\b"
)

_PASSWORD_PATTERN = re.compile(
    r"(?:password|passwd|pwd)\s*[:=]\s*\S+",
    re.IGNORECASE,
)

# Complete precise address — heuristic: 6+ consecutive digits OR detailed street-level
_ADDRESS_PATTERN = re.compile(
    r"(?:省|市|区|县|镇|街道|路|弄|号|栋|单元|室)\s*[\d一-鿿-]{4,}",
)


# ── Detection function ───────────────────────────────────────────────────

def contains_sensitive_info(text: str) -> str | None:
    """Return a human-readable rejection reason if *text* contains sensitive data.

    Returns ``None`` if the text is safe to store.
    """
    if _JWT_PATTERN.search(text):
        return "检测到 JWT 令牌，禁止存储"

    if _BANK_CARD_PATTERN.search(text):
        return "检测到银行卡号，禁止存储"

    if _CN_ID_PATTERN.search(text):
        return "检测到身份证号，禁止存储"

    if _API_KEY_PATTERN.search(text):
        return "检测到 API Key，禁止存储"

    if _PASSWORD_PATTERN.search(text):
        return "检测到密码信息，禁止存储"

    if _ADDRESS_PATTERN.search(text):
        return "检测到详细地址信息，禁止存储"

    return None


# ── Batch check for dict/structured_data ─────────────────────────────────

def sanitize_memory_content(content: str, structured_data: dict | None) -> str | None:
    """Check both content and structured_data for sensitive info.

    Returns ``None`` if safe, or a rejection reason string.
    """
    # Check plain-text content
    reason = contains_sensitive_info(content)
    if reason is not None:
        return reason

    # Check structured_data values (shallow)
    if structured_data:
        for _key, value in structured_data.items():
            if isinstance(value, str):
                reason = contains_sensitive_info(value)
                if reason is not None:
                    return f"structured_data.{_key}: {reason}"

    return None
