"""Idempotent seed script — safe to run multiple times.

Creates test users, products, and sample orders.
Uses ON CONFLICT DO NOTHING for idempotency.
"""

import asyncio
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import _get_session_factory
from app.models.enums import LogisticsStatus, OrderStatus
from app.models.logistics_record import LogisticsRecord
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User
from app.security.password import hash_password

SEED_PASSWORD = hash_password("password123")

USERS = [
    {"email": "admin@test.com", "full_name": "Admin User", "role": "ADMIN"},
    {"email": "operator@test.com", "full_name": "Operator User", "role": "OPERATOR"},
    {"email": "customer@test.com", "full_name": "Alice Customer", "role": "CUSTOMER"},
    {"email": "customer2@test.com", "full_name": "Bob Customer", "role": "CUSTOMER"},
    {"email": "customer3@test.com", "full_name": "Carol Customer", "role": "CUSTOMER"},
]

PRODUCTS = [
    {"name": "Wireless Headphones", "category": "ELECTRONICS", "price": Decimal("299.00"), "stock": 50},
    {"name": "Smartphone X1", "category": "ELECTRONICS", "price": Decimal("4999.00"), "stock": 20},
    {"name": "Cotton T-Shirt", "category": "CLOTHING", "price": Decimal("79.00"), "stock": 100},
    {"name": "Running Shoes", "category": "SPORTS", "price": Decimal("599.00"), "stock": 30},
    {"name": "Organic Snack Box", "category": "FOOD", "price": Decimal("128.00"), "stock": 60},
    {"name": "Desk Lamp LED", "category": "HOME", "price": Decimal("189.00"), "stock": 40},
    {"name": "USB-C Charging Cable", "category": "ELECTRONICS", "price": Decimal("29.00"), "stock": 200},
    {"name": "Winter Jacket", "category": "CLOTHING", "price": Decimal("899.00"), "stock": 15},
    {"name": "Yoga Mat", "category": "SPORTS", "price": Decimal("149.00"), "stock": 45},
    {"name": "Coffee Beans 500g", "category": "FOOD", "price": Decimal("88.00"), "stock": 80},
]


async def seed_users(session: AsyncSession) -> dict[str, User]:
    from sqlalchemy import select as sa_select
    # Check existing
    result = await session.execute(sa_select(User))
    existing = {u.email: u for u in result.scalars().all()}
    for u_def in USERS:
        if u_def["email"] not in existing:
            user = User(
                email=u_def["email"], hashed_password=SEED_PASSWORD,
                full_name=u_def["full_name"], role=u_def["role"],
            )
            session.add(user)
    await session.flush()
    result = await session.execute(sa_select(User))
    return {u.email: u for u in result.scalars().all()}


async def seed_products(session: AsyncSession) -> list[Product]:
    from sqlalchemy import select as sa_select
    result = await session.execute(sa_select(Product))
    existing_names = {p.name for p in result.scalars().all()}
    for p_def in PRODUCTS:
        if p_def["name"] not in existing_names:
            session.add(Product(
                name=p_def["name"], category=p_def["category"],
                price=p_def["price"], stock=p_def["stock"],
            ))
    await session.flush()
    result = await session.execute(sa_select(Product).order_by(Product.name))
    return list(result.scalars().all())


def _make_order_number(seq: int) -> str:
    return f"ORD-{seq:06d}"


async def seed_orders(session: AsyncSession, users: dict, products: list[Product]) -> None:
    customer = users.get("customer@test.com")
    if customer is None:
        return

    product_map = {p.name: p for p in products}

    # Order 1: PENDING_PAYMENT (headphones)
    hp = product_map["Wireless Headphones"]
    o1_exists = await session.execute(
        text("SELECT 1 FROM orders WHERE order_number = 'ORD-000001'")
    )
    if o1_exists.scalar() is None:
        o1 = Order(
            user_id=customer.id, order_number="ORD-000001",
            status=OrderStatus.PENDING_PAYMENT.value,
            total_amount=hp.price * 2, shipping_address="北京市朝阳区测试路100号",
            shipping_fee=Decimal("0"),
            created_at=datetime.now(UTC) - timedelta(hours=2),
        )
        session.add(o1)
        await session.flush()
        session.add(OrderItem(
            order_id=o1.id, product_id=hp.id, product_name=hp.name,
            unit_price=hp.price, quantity=2, subtotal=hp.price * 2,
        ))
        await session.flush()

    # Order 2: PAID (shoes) — ready to ship
    shoes = product_map["Running Shoes"]
    o2_exists = await session.execute(
        text("SELECT 1 FROM orders WHERE order_number = 'ORD-000002'")
    )
    if o2_exists.scalar() is None:
        o2 = Order(
            user_id=customer.id, order_number="ORD-000002",
            status=OrderStatus.PAID.value,
            total_amount=shoes.price, shipping_address="北京市朝阳区测试路100号",
            shipping_fee=Decimal("0"), paid_amount=shoes.price,
            paid_at=datetime.now(UTC) - timedelta(hours=1),
            created_at=datetime.now(UTC) - timedelta(hours=3),
        )
        session.add(o2)
        await session.flush()
        session.add(OrderItem(
            order_id=o2.id, product_id=shoes.id, product_name=shoes.name,
            unit_price=shoes.price, quantity=1, subtotal=shoes.price,
        ))
        await session.flush()

    # Order 3: SHIPPED (lamp)
    lamp = product_map["Desk Lamp LED"]
    o3_exists = await session.execute(
        text("SELECT 1 FROM orders WHERE order_number = 'ORD-000003'")
    )
    if o3_exists.scalar() is None:
        o3 = Order(
            user_id=customer.id, order_number="ORD-000003",
            status=OrderStatus.SHIPPED.value,
            total_amount=lamp.price, shipping_address="北京市朝阳区测试路100号",
            shipping_fee=Decimal("0"), paid_amount=lamp.price,
            paid_at=datetime.now(UTC) - timedelta(days=1),
            shipped_at=datetime.now(UTC) - timedelta(hours=12),
            created_at=datetime.now(UTC) - timedelta(days=2),
        )
        session.add(o3)
        await session.flush()
        session.add(OrderItem(
            order_id=o3.id, product_id=lamp.id, product_name=lamp.name,
            unit_price=lamp.price, quantity=1, subtotal=lamp.price,
        ))
        await session.flush()
        tn = f"SF{random.randint(10000000000, 99999999999)}"
        session.add(LogisticsRecord(
            order_id=o3.id, tracking_number=tn, carrier="SF Express",
            status=LogisticsStatus.IN_TRANSIT.value, current_location="Shanghai Distribution Center",
            events=[{
                "timestamp": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "status": "PICKED_UP", "location": "Beijing DC",
                "description": "Package picked up",
            }, {
                "timestamp": (datetime.now(UTC) - timedelta(hours=12)).isoformat(),
                "status": "IN_TRANSIT", "location": "Shanghai DC",
                "description": "Package in transit",
            }],
        ))
        await session.flush()

    # Order 4: DELIVERED (snack)
    snack = product_map["Organic Snack Box"]
    o4_exists = await session.execute(
        text("SELECT 1 FROM orders WHERE order_number = 'ORD-000004'")
    )
    if o4_exists.scalar() is None:
        o4 = Order(
            user_id=customer.id, order_number="ORD-000004",
            status=OrderStatus.DELIVERED.value,
            total_amount=snack.price * 3, shipping_address="北京市朝阳区测试路100号",
            shipping_fee=Decimal("0"), paid_amount=snack.price * 3,
            paid_at=datetime.now(UTC) - timedelta(days=5),
            shipped_at=datetime.now(UTC) - timedelta(days=4),
            delivered_at=datetime.now(UTC) - timedelta(days=3),
            created_at=datetime.now(UTC) - timedelta(days=7),
        )
        session.add(o4)
        await session.flush()
        session.add(OrderItem(
            order_id=o4.id, product_id=snack.id, product_name=snack.name,
            unit_price=snack.price, quantity=3, subtotal=snack.price * 3,
        ))
        await session.flush()


async def main() -> None:
    factory = _get_session_factory()
    async with factory() as session:
        print("Seeding users...")  # noqa: T201
        users = await seed_users(session)
        print(f"  {len(users)} users present")

        print("Seeding products...")
        products = await seed_products(session)
        print(f"  {len(products)} products present")

        print("Seeding orders...")
        await seed_orders(session, users, products)

        await session.commit()
        print("Seed complete (idempotent).")


if __name__ == "__main__":
    asyncio.run(main())
