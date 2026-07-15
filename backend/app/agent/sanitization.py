"""LLM data minimization — field allowlists for tool outputs and context.

All data sent to external LLM providers must pass through these projections.
Internal IDs, PII, and credentials are stripped before any LLM call.
"""

# Fields to KEEP when sending order data to the LLM
ORDER_LLM_FIELDS = frozenset({
    "order_number", "status", "total_amount", "paid_amount",
    "shipping_fee", "paid_at", "shipped_at", "delivered_at",
})

ORDER_ITEM_LLM_FIELDS = frozenset({
    "product_name", "quantity", "unit_price",
})

# Fields to KEEP when sending ticket data to the LLM
TICKET_LLM_FIELDS = frozenset({
    "ticket_number", "intent", "status", "created_at",
    "reject_code", "reject_reason",
})

# Fields STRIPPED from all LLM-bound data (always removed)
STRIP_FIELDS = frozenset({
    "user_id", "email", "full_name", "hashed_password",
    "access_token", "refresh_token", "Authorization",
    "shipping_address", "phone", "ip_address", "user_agent",
    "coupon_code", "version", "id", "product_id",
    "order_item_id", "subtotal", "discount_amount",
})


def project_order_for_llm(raw: dict) -> dict:
    """Strip PII and internal IDs from order data before sending to LLM."""
    result: dict = {}
    for k in ORDER_LLM_FIELDS:
        if k in raw:
            result[k] = raw[k]
    if "items" in raw:
        result["items"] = [
            {ik: iv for ik, iv in item.items() if ik in ORDER_ITEM_LLM_FIELDS}
            for item in raw["items"]
        ]
    return result


def project_ticket_for_llm(raw: dict) -> dict:
    """Strip PII and internal IDs from ticket data before sending to LLM."""
    return {k: v for k, v in raw.items() if k in TICKET_LLM_FIELDS}


def project_for_llm(tool_name: str, raw: dict) -> dict:
    """Select the right projection based on tool name."""
    projections = {
        "get_order": project_order_for_llm,
        "list_orders": lambda r: {
            "items": [project_order_for_llm(o) for o in r.get("items", [])],
            "total": r.get("total"), "page": r.get("page"),
        },
        "get_after_sales_ticket": project_ticket_for_llm,
        "list_after_sales_tickets": lambda r: {
            "items": [project_ticket_for_llm(t) for t in r.get("items", [])],
            "total": r.get("total"), "page": r.get("page"),
        },
    }
    projector = projections.get(tool_name)
    if projector is not None:
        return projector(raw)  # type: ignore[no-untyped-call]
    return raw


# Fields to KEEP when sending policy data to the LLM
POLICY_LLM_FIELDS = frozenset({
    "policy_key", "title", "category", "content_summary",
    "snippet", "similarity_score", "version",
})


def project_policy_for_llm(policy: dict) -> dict:
    """Strip internal fields (UUIDs, hashes, full content) from policy results."""
    return {
        k: v for k, v in policy.items()
        if k in POLICY_LLM_FIELDS
    }


def strip_pii_from_dict(data: dict) -> dict:
    """Recursively remove PII fields from a dict for trace/tool_log storage."""
    if not isinstance(data, dict):
        return data
    result: dict = {}
    for k, v in data.items():
        if k.lower() in {f.lower() for f in STRIP_FIELDS}:
            continue
        if isinstance(v, dict):
            result[k] = strip_pii_from_dict(v)
        elif isinstance(v, list):
            result[k] = [
                strip_pii_from_dict(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            result[k] = v
    return result
