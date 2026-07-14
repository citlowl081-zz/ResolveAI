"""Python enum definitions matching PostgreSQL enum types."""

import enum


class UserRole(enum.StrEnum):
    CUSTOMER = "CUSTOMER"
    OPERATOR = "OPERATOR"
    ADMIN = "ADMIN"


class RiskLevel(enum.StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ProductCategory(enum.StrEnum):
    ELECTRONICS = "ELECTRONICS"
    CLOTHING = "CLOTHING"
    FOOD = "FOOD"
    HOME = "HOME"
    SPORTS = "SPORTS"
    OTHER = "OTHER"


class OrderStatus(enum.StrEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class LogisticsStatus(enum.StrEnum):
    PENDING = "PENDING"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"


class IntentType(enum.StrEnum):
    LOGISTICS_INQUIRY = "LOGISTICS_INQUIRY"
    PRE_SHIP_REFUND = "PRE_SHIP_REFUND"
    QUALITY_REFUND = "QUALITY_REFUND"
    EXCHANGE = "EXCHANGE"
    MISSING_PARTS = "MISSING_PARTS"
    OTHER = "OTHER"


class TicketStatus(enum.StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ResolutionType(enum.StrEnum):
    REFUND = "REFUND"
    EXCHANGE = "EXCHANGE"
    RESHIPMENT = "RESHIPMENT"
    INFO_ONLY = "INFO_ONLY"


class RefundType(enum.StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    SHIPPING_FEE = "SHIPPING_FEE"


class ReshipmentStatus(enum.StrEnum):
    CREATED = "CREATED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class SessionStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class MessageRole(enum.StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    TOOL = "TOOL"
    SYSTEM = "SYSTEM"
