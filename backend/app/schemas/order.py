"""Order request/response schemas."""

from pydantic import BaseModel, Field


class OrderItemRequest(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)


class OrderCreateRequest(BaseModel):
    items: list[OrderItemRequest] = Field(min_length=1)
    shipping_address: str = Field(min_length=1, max_length=500)
    shipping_fee: str = Field(default="0", pattern=r"^\d+(\.\d{1,2})?$")


class VersionedRequest(BaseModel):
    expected_version: int = Field(ge=1)


class CancelRequest(VersionedRequest):
    reason: str = Field(default="", max_length=500)


class ShipRequest(VersionedRequest):
    tracking_number: str | None = None
    carrier: str = "SF Express"


class OrderItemResponse(BaseModel):
    product_id: str
    product_name: str
    unit_price: str
    quantity: int
    subtotal: str


class OrderResponse(BaseModel):
    id: str
    order_number: str
    status: str
    total_amount: str
    discount_amount: str
    paid_amount: str
    shipping_address: str
    shipping_fee: str
    coupon_code: str | None = None
    paid_at: str | None = None
    shipped_at: str | None = None
    delivered_at: str | None = None
    cancelled_at: str | None = None
    cancel_reason: str | None = None
    version: int
    created_at: str | None = None
    items: list[OrderItemResponse] = Field(default_factory=list)


class OrderSummaryResponse(BaseModel):
    id: str
    order_number: str
    status: str
    total_amount: str
    created_at: str | None = None
