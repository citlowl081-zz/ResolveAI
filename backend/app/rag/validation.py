"""Policy key validation — stable, reusable validation logic.

The policy_key format is:
    ``POL-{PREFIX}-{NNN}``

where *PREFIX* is a 3-letter code drawn from ``POLICY_KEY_PREFIXES``
and *NNN* is a zero-padded 3-digit sequence number.

Validation enforces:
1. Format: ``^POL-(RET|REF|EXC|RES|LOG|RISK|SOP|GEN)-\\d{3}$``
2. Prefix → ``PolicyCategory`` consistency (via
   ``validate_policy_key_and_category``).
"""

from __future__ import annotations

import re
from typing import Any

from app.models.enums import PolicyCategory

# ── Allowed 3-letter prefixes ──────────────────────────────────────────
POLICY_KEY_PREFIXES: frozenset[str] = frozenset(
    {"RET", "REF", "EXC", "RES", "LOG", "RISK", "SOP", "GEN"}
)

# ── Compiled regex (module-level singleton) ────────────────────────────
POLICY_KEY_RE: re.Pattern[str] = re.compile(
    r"^POL-(" + "|".join(sorted(POLICY_KEY_PREFIXES)) + r")-\d{3}$"
)


def validate_policy_key(key: str) -> str:
    """Validate *key* against the policy_key format.

    Returns the normalised key on success.  Raises ``ValueError`` with a
    human-readable message on failure — the caller is responsible for
    translating this into an HTTP error, Pydantic ``ValidationError``, or
    a log entry as appropriate.

    The format is strict:
    - ``POL-`` prefix (uppercase)
    - 3-letter category prefix from ``POLICY_KEY_PREFIXES``
    - ``-``
    - Exactly 3 digits (``000``–``999``)
    """
    if not isinstance(key, str) or not key.strip():
        raise ValueError("policy_key must be a non-empty string")
    key = key.strip()
    if not POLICY_KEY_RE.match(key):
        raise ValueError(
            f"Invalid policy_key '{key}'. "
            f"Expected format: POL-<prefix>-NNN where prefix is one of "
            f"{sorted(POLICY_KEY_PREFIXES)} and NNN is a 3-digit number."
        )
    return key


def validate_policy_key_and_category(key: str, category: Any) -> tuple[str, PolicyCategory]:
    """Validate *key* format **and** prefix–category consistency.

    Returns ``(normalised_key, category_enum)`` on success.

    Parameters
    ----------
    key:
        The raw policy_key string (e.g. ``"POL-REF-001"``).
    category:
        A ``PolicyCategory`` member or a string matching a
        ``PolicyCategory`` value (e.g. ``"REFUND"`` or
        ``PolicyCategory.REFUND``).

    Raises
    ------
    ValueError:
        If *key* fails format validation.
    ValueError:
        If *category* is not a recognised ``PolicyCategory``.
    ValueError:
        If the prefix in *key* does not match *category*.
    """
    normalised = validate_policy_key(key)

    # Resolve category to the PolicyCategory enum
    if isinstance(category, PolicyCategory):
        cat = category
    elif isinstance(category, str):
        try:
            cat = PolicyCategory(category)
        except ValueError as exc:
            raise ValueError(
                f"Unknown policy category '{category}'. "
                f"Allowed: {[c.value for c in PolicyCategory]}"
            ) from exc
    else:
        raise ValueError(
            f"category must be a PolicyCategory or str, got {type(category).__name__}"
        )

    # Extract prefix from the key by splitting on "-"
    # "POL-REF-001" → ["POL", "REF", "001"] → "REF"
    # "POL-RISK-001" → ["POL", "RISK", "001"] → "RISK"
    parts = normalised.split("-")
    if len(parts) != 3:
        raise ValueError(f"policy_key '{normalised}' must have exactly 3 parts separated by '-'")
    prefix = parts[1]
    expected_cat = PolicyCategory.from_prefix(prefix)

    if cat is not expected_cat:
        raise ValueError(
            f"policy_key prefix '{prefix}' maps to category "
            f"'{expected_cat.value}', but category '{cat.value}' was provided. "
            f"Use prefix '{prefix}' with category '{expected_cat.value}'."
        )

    return normalised, cat
