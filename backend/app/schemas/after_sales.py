"""After-sales request/response schemas."""


from pydantic import BaseModel, Field

# ── Request Schemas ───────────────────────────────────────────────────

class RequestedItem(BaseModel):
    order_item_id: str
    product_id: str
    quantity: int = Field(ge=1)
    reason_code: str = Field(min_length=1, max_length=50)


class TicketCreateRequest(BaseModel):
    order_id: str
    intent: str = Field(min_length=1, max_length=50)
    requested_items: list[RequestedItem] = Field(min_length=1)
    customer_request: str = Field(default="", max_length=2000)


class TicketCancelRequest(BaseModel):
    expected_version: int = Field(ge=1)


class TicketApproveRequest(BaseModel):
    expected_version: int = Field(ge=1)


class TicketRejectRequest(BaseModel):
    expected_version: int = Field(ge=1)
    reject_reason: str = Field(default="", max_length=500)


class RefundExecuteRequest(BaseModel):
    expected_version: int = Field(ge=1)


class ReshipmentCreateRequest(BaseModel):
    expected_version: int = Field(ge=1)


class ReshipmentShipRequest(BaseModel):
    expected_version: int = Field(ge=1)
    tracking_number: str | None = None
    carrier: str = "SF Express"


class ReshipmentDeliverRequest(BaseModel):
    expected_version: int = Field(ge=1)


class ReshipmentCancelRequest(BaseModel):
    expected_version: int = Field(ge=1)


# ── Response Schemas ──────────────────────────────────────────────────

class RequestedItemResponse(BaseModel):
    order_item_id: str
    product_id: str
    quantity: int
    reason_code: str


class TicketResponse(BaseModel):
    id: str
    ticket_number: str
    user_id: str
    order_id: str
    intent: str
    status: str
    resolution_type: str | None = None
    customer_request: str | None = None
    requested_items: list[dict]
    operator_notes: str | None = None
    proposed_solution: dict | None = None
    resolution_result: dict | None = None
    reject_reason: str | None = None
    reject_code: str | None = None
    version: int
    created_at: str | None = None
    updated_at: str | None = None
    completed_at: str | None = None


class RefundItemResponse(BaseModel):
    order_item_id: str
    product_id: str
    quantity: int
    unit_price: str
    item_refund_amount: str


class RefundResponse(BaseModel):
    id: str
    ticket_id: str
    order_id: str
    user_id: str
    refund_amount: str
    shipping_refund_amount: str
    refund_type: str
    refund_reason: str | None = None
    refund_items: list[dict]
    calculation_breakdown: dict | None = None
    rule_version: str | None = None
    processed_by: str | None = None
    created_at: str | None = None


class ReshipmentResponse(BaseModel):
    id: str
    ticket_id: str
    original_order_id: str
    user_id: str
    reshipment_number: str
    missing_items: list[dict]
    shipping_address: str
    status: str
    tracking_number: str | None = None
    carrier: str | None = None
    shipped_at: str | None = None
    delivered_at: str | None = None
    version: int
    processed_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
