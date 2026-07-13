"""Python enum definitions matching PostgreSQL enum types."""

import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    OPERATOR = "OPERATOR"
    ADMIN = "ADMIN"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ProductCategory(str, enum.Enum):
    ELECTRONICS = "ELECTRONICS"
    CLOTHING = "CLOTHING"
    FOOD = "FOOD"
    HOME = "HOME"
    SPORTS = "SPORTS"
    OTHER = "OTHER"


class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class LogisticsStatus(str, enum.Enum):
    PENDING = "PENDING"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"
