"""Request fingerprint computation for after-sales ticket deduplication."""

import hashlib
import json


def compute_request_fingerprint(requested_items: list[dict]) -> str:
    """Compute SHA-256 of canonical requested_items for active-ticket dedup.

    The fingerprint is computed server-side from validated requested_items.
    Clients do NOT submit it — the service layer computes it.

    Canonical form: sorted by order_item_id, with only the four key fields.
    """
    canonical = [
        {
            "order_item_id": str(item["order_item_id"]),
            "product_id": str(item["product_id"]),
            "quantity": int(item["quantity"]),
            "reason_code": str(item.get("reason_code", "")),
        }
        for item in requested_items
    ]
    canonical.sort(key=lambda x: str(x["order_item_id"]))

    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
