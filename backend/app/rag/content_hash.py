"""Stable content hashing for policy documents — BLAKE2b over canonical JSON.

Only **semantic fields** are included in the hash so that two rows with
identical content but different version numbers / statuses / timestamps
produce the same digest.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# ── Semantic fields included in the content hash ──────────────────────
_HASH_FIELDS = frozenset({
    "title",
    "category",
    "issue_types",
    "content",
    "content_summary",
    "metadata_filter",
    "effective_date",
    "expiration_date",
    "source",
})


def compute_content_hash(doc: dict[str, Any]) -> str:
    """Return a BLAKE2b hex digest of the canonicalised semantic fields.

    Fields included:
        ``title``, ``category``, ``issue_types``, ``content``,
        ``content_summary``, ``metadata_filter``, ``effective_date``,
        ``expiration_date``, ``source``

    Fields **excluded**:
        ``id``, ``policy_key``, ``version``, ``status``,
        ``superseded_by``, ``created_at``, ``updated_at``, and any
        other internal / DB-only fields.

    *issue_types* is sorted before hashing so that ``["A","B"]`` and
    ``["B","A"]`` produce the same hash.  ``metadata_filter`` is
    recursively canonicalised so that key ordering is deterministic.
    """
    payload: dict[str, Any] = {
        "title": doc.get("title", ""),
        "category": doc.get("category", ""),
        "issue_types": sorted(doc.get("issue_types", [])),
        "content": doc.get("content", ""),
        "content_summary": _or_empty(doc.get("content_summary")),
        "metadata_filter": _canonicalize_metadata(doc.get("metadata_filter", {})),
        "effective_date": _date_to_str(doc.get("effective_date")),
        "expiration_date": _date_to_str(doc.get("expiration_date")),
        "source": _or_empty(doc.get("source")),
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.blake2b(
        canonical.encode("utf-8"), digest_size=32
    ).hexdigest()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _date_to_str(value: Any) -> Any:
    """Convert a date/datetime to ISO string, pass through everything else."""
    from datetime import date as date_type
    from datetime import datetime as dt_type

    if isinstance(value, (date_type, dt_type)):
        return value.isoformat()
    return _or_empty(value)


def _or_empty(value: Any) -> Any:
    """Return *value* unchanged, or  ``""`` / ``None`` for falsy values.

    Dates and booleans are kept as-is; ``None`` and empty strings are
    normalised to ``None`` so that ``""`` and ``null`` hash identically
    in the JSON output (``sort_keys`` + ``separators`` already handles
    this, but being explicit is safer).
    """
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _canonicalize_metadata(obj: Any) -> Any:
    """Recursively canonicalise *obj* for deterministic serialisation.

    - ``dict`` entries are sorted by key, values recurse.
    - ``list`` elements recurse.
    - Scalars pass through unchanged.
    """
    if isinstance(obj, dict):
        return {
            k: _canonicalize_metadata(v)
            for k, v in sorted(obj.items())
        }
    if isinstance(obj, list):
        return [_canonicalize_metadata(item) for item in obj]
    return obj
