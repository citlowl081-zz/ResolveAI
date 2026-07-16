"""Demo seed script — idempotent, repeatable, safe for local demonstration.

Creates demo accounts, products, orders, logistics, agent data.
All data fictional. Passwords from DEMO_* env vars or safe demo defaults.
"""

import asyncio
import os
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import _get_session_factory
from app.models.enums import LogisticsStatus, OrderStatus
from app.models.logistics_record import LogisticsRecord
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User
from app.security.password import hash_password

_DEMO_CUST_EMAIL = os.getenv("DEMO_CUSTOMER_EMAIL", "demo@example.com")
_DEMO_CUST_PASS = os.getenv("DEMO_CUSTOMER_PASSWORD", "demo123456")
_DEMO_ADMIN_EMAIL = os.getenv("DEMO_ADMIN_EMAIL", "admin@example.com")
_DEMO_ADMIN_PASS = os.getenv("DEMO_ADMIN_PASSWORD", "admin123456")

CUST_HASH = hash_password(_DEMO_CUST_PASS)
ADMIN_HASH = hash_password(_DEMO_ADMIN_PASS)

USERS = [
    {"email": _DEMO_ADMIN_EMAIL, "full_name": "Admin Demo", "role": "ADMIN", "pw": ADMIN_HASH},
    {"email": _DEMO_CUST_EMAIL, "full_name": "Demo Customer", "role": "CUSTOMER", "pw": CUST_HASH},
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


async def seed_users(session: AsyncSession) -> dict:
    from sqlalchemy import select as sa_select
    result = await session.execute(sa_select(User))
    existing = {u.email: u for u in result.scalars().all()}
    for u_def in USERS:
        if u_def["email"] not in existing:
            user = User(
                email=u_def["email"], hashed_password=u_def["pw"],
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


async def seed_orders(session: AsyncSession, users: dict, products: list[Product]) -> None:
    customer = users.get(_DEMO_CUST_EMAIL)
    if customer is None:
        return
    product_map = {p.name: p for p in products}

    def _order_exists(num: str) -> bool:
        return False  # unused; checked via order_number query below

    orders_to_seed = [
        ("ORD-000001", "Wireless Headphones", OrderStatus.DELIVERED.value, 2,
         timedelta(days=5), timedelta(days=4), timedelta(days=3), timedelta(days=7)),
        ("ORD-000002", "Running Shoes", OrderStatus.PAID.value, 1,
         timedelta(hours=1), None, None, timedelta(hours=3)),
        ("ORD-000003", "Desk Lamp LED", OrderStatus.SHIPPED.value, 1,
         timedelta(days=1), timedelta(hours=12), None, timedelta(days=2)),
    ]

    for order_num, pname, status, qty, paid_delta, ship_delta, deliv_delta, create_delta in orders_to_seed:
        exists = await session.execute(sa_text("SELECT 1 FROM orders WHERE order_number = :n"), {"n": order_num})
        if exists.scalar() is not None:
            continue
        p = product_map[pname]
        now = datetime.now(UTC)
        o = Order(
            user_id=customer.id, order_number=order_num, status=status,
            total_amount=p.price * qty, shipping_address="Demo Address",
            shipping_fee=Decimal("0"), paid_amount=p.price * qty,
            paid_at=now - paid_delta,
            shipped_at=now - ship_delta if ship_delta else None,
            delivered_at=now - deliv_delta if deliv_delta else None,
            created_at=now - create_delta,
        )
        session.add(o)
        await session.flush()
        session.add(OrderItem(order_id=o.id, product_id=p.id, product_name=p.name, unit_price=p.price, quantity=qty, subtotal=p.price * qty))
        await session.flush()
        # Add logistics for shipped orders (idempotent by order_id)
        if status == OrderStatus.SHIPPED.value:
            log_exists = await session.execute(
                sa_text("SELECT 1 FROM logistics_records WHERE order_id = :oid"), {"oid": o.id}
            )
            if log_exists.scalar() is None:
                tn = f"SF{random.randint(10000000000, 99999999999)}"
                session.add(LogisticsRecord(order_id=o.id, tracking_number=tn, carrier="SF Express", status=LogisticsStatus.IN_TRANSIT.value, current_location="Shanghai DC", events=[]))
                await session.flush()


async def seed_agent_data(session: AsyncSession, users: dict) -> None:
    """Create a demo agent session with messages for the demo customer."""
    from app.models.agent_message import AgentMessage
    from app.models.agent_session import AgentSession
    from app.models.enums import MessageRole

    customer = users.get(_DEMO_CUST_EMAIL)
    if customer is None:
        return
    from sqlalchemy import select as sa_select
    result = await session.execute(sa_select(AgentSession).where(AgentSession.user_id == customer.id))
    if result.scalar_one_or_none() is not None:
        return  # Already seeded

    sess = AgentSession(user_id=customer.id, status="ACTIVE", message_count=2)
    session.add(sess)
    await session.flush()
    session.add(AgentMessage(session_id=sess.id, turn_id=sess.id, role=MessageRole.USER.value, content="Hello, I want to check my order status.", sequence_number=1, turn_sequence=0))
    session.add(AgentMessage(session_id=sess.id, turn_id=sess.id, role=MessageRole.ASSISTANT.value, content="Your order ORD-000003 is in transit.", sequence_number=2, turn_sequence=1))
    await session.flush()


async def main() -> None:
    factory = _get_session_factory()
    async with factory() as session:
        print("Seeding demo data...")
        users = await seed_users(session)
        print(f"  Users: {len(users)}")
        products = await seed_products(session)
        print(f"  Products: {len(products)}")
        await seed_orders(session, users, products)
        print("  Orders: 3 (DELIVERED, PAID, SHIPPED)")
        await seed_agent_data(session, users)
        print("  Agent session: 1 demo conversation")
        await session.commit()
        print("Seed complete (idempotent).")
        print(f"  Demo Customer: {_DEMO_CUST_EMAIL} / {_DEMO_CUST_PASS}")
        print(f"  Demo Admin:    {_DEMO_ADMIN_EMAIL} / {_DEMO_ADMIN_PASS}")


if __name__ == "__main__":
    asyncio.run(main())
