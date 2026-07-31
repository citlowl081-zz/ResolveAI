"""Demo seed script — idempotent, repeatable, safe for local demonstration.

Creates demo accounts, products, orders, logistics, agent data.
All data fictional. Passwords from DEMO_* env vars or safe demo defaults.
"""

import asyncio
import os
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
    {"email": _DEMO_ADMIN_EMAIL, "full_name": "演示管理员", "role": "ADMIN", "pw": ADMIN_HASH},
    {"email": _DEMO_CUST_EMAIL, "full_name": "演示顾客", "role": "CUSTOMER", "pw": CUST_HASH},
]

def _product(sku: str, name: str, price: str, stock: int, description: str) -> dict:
    return {
        "sku": sku, "name": name, "category": "ELECTRONICS", "price": Decimal(price),
        "stock": stock, "description": description,
    }


PRODUCTS = [
    _product("RA-AUD-001", "Aurora Buds Pro 无线降噪耳机", "699.00", 80, "自适应降噪与通透模式，适合通勤和桌面办公。"),
    _product("RA-AUD-002", "Sonic Air 开放式蓝牙耳机", "499.00", 65, "开放式佩戴，兼顾环境感知与舒适聆听。"),
    _product("RA-AUD-003", "Studio One 桌面监听音箱", "1299.00", 24, "紧凑型双单元桌面音箱，支持多种音频输入。"),
    _product("RA-AUD-004", "VoiceLink USB 麦克风", "459.00", 42, "即插即用的心形指向麦克风，适合会议与创作。"),
    _product("RA-PER-001", "FlowKeys 机械键盘", "599.00", 55, "多设备切换与热插拔轴座，提升桌面输入效率。"),
    _product("RA-PER-002", "Glide Pro 无线鼠标", "329.00", 90, "轻量化人体工学设计，支持双模连接。"),
    _product("RA-PER-003", "VisionBar 2K 摄像头", "549.00", 36, "2K 清晰视频与自动曝光，适合远程会议。"),
    _product("RA-PER-004", "DockMate 12 合 1 扩展坞", "799.00", 38, "一线扩展显示、网络、读卡和高速数据接口。"),
    _product("RA-MOB-001", "PowerCube 65W 氮化镓充电器", "239.00", 120, "三口快充与折叠插脚，适合差旅携带。"),
    _product("RA-MOB-002", "MagFlow 磁吸无线充电座", "199.00", 88, "立式磁吸充电，方便查看桌面通知。"),
    _product("RA-MOB-003", "FlexLine 编织数据线", "59.00", 260, "耐弯折编织线材，支持快速充电与数据传输。"),
    _product("RA-MOB-004", "TravelHub 移动电源", "299.00", 72, "大容量双向快充，配备电量显示。"),
    _product("RA-OFF-001", "Halo Monitor 智能屏幕挂灯", "369.00", 46, "非对称照明减少屏幕反光，支持色温调节。"),
    _product("RA-OFF-002", "ErgoLift 笔记本支架", "269.00", 75, "多档高度调节，改善桌面视线与散热。"),
    _product("RA-OFF-003", "DeskFlow 智能插座", "129.00", 110, "定时与远程控制，为桌面设备提供用电管理。"),
    _product("RA-OFF-004", "QuietDesk 桌面静音风扇", "219.00", 58, "低噪送风与多档调节，适合安静办公。"),
    _product("RA-WEA-001", "Pulse Watch 智能手表", "899.00", 32, "运动记录、消息提醒与全天候健康趋势。"),
    _product("RA-WEA-002", "Motion Band 健身手环", "299.00", 64, "轻量运动监测与长续航设计。"),
    _product("RA-WEA-003", "Sleep Ring 睡眠监测指环", "1099.00", 18, "夜间睡眠趋势记录，轻巧无屏佩戴。"),
    _product("RA-HOM-001", "HomeSense 智能网关", "299.00", 40, "连接多类智能设备，构建本地自动化场景。"),
    _product("RA-HOM-002", "AirGuard 空气质量传感器", "399.00", 34, "监测温湿度与空气质量趋势。"),
    _product("RA-HOM-003", "LightCore 智能氛围灯", "259.00", 67, "多场景灯光与桌面联动控制。"),
    _product("RA-HOM-004", "SecureEye 室内智能摄像头", "469.00", 28, "移动侦测与隐私遮蔽，守护室内空间。"),
]

_LEGACY_PRODUCT_RENAMES = {
    "Wireless Headphones": "Aurora Buds Pro 无线降噪耳机",
    "Running Shoes": "FlowKeys 机械键盘",
    "Desk Lamp LED": "Halo Monitor 智能屏幕挂灯",
    "QuietDesk 桌面降噪风扇": "QuietDesk 桌面静音风扇",
}
_LEGACY_PRODUCT_NAMES = {
    "Wireless Headphones", "Smartphone X1", "Cotton T-Shirt", "Running Shoes",
    "Organic Snack Box", "Desk Lamp LED", "USB-C Charging Cable", "Winter Jacket",
    "Yoga Mat", "Coffee Beans 500g",
}


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
        else:
            existing[u_def["email"]].full_name = u_def["full_name"]
    await session.flush()
    result = await session.execute(sa_select(User))
    return {u.email: u for u in result.scalars().all()}


async def seed_products(session: AsyncSession) -> list[Product]:
    from sqlalchemy import select as sa_select

    result = await session.execute(sa_select(Product))
    existing_products = list(result.scalars().all())
    by_sku: dict[str, list[Product]] = {}
    for existing_product in existing_products:
        if existing_product.sku:
            by_sku.setdefault(existing_product.sku, []).append(existing_product)
    duplicate_skus = sorted(sku for sku, rows in by_sku.items() if len(rows) > 1)
    if duplicate_skus:
        raise RuntimeError(f"Duplicate product SKU(s) detected: {', '.join(duplicate_skus)}")

    legacy_by_target = {target: legacy for legacy, target in _LEGACY_PRODUCT_RENAMES.items()}
    seeded: list[Product] = []
    for definition in PRODUCTS:
        sku = str(definition["sku"])
        product: Product | None = next(iter(by_sku.get(sku, [])), None)
        if product is None:
            accepted_names = {str(definition["name"])}
            legacy_name = legacy_by_target.get(str(definition["name"]))
            if legacy_name:
                accepted_names.add(legacy_name)
            product = next((p for p in existing_products if p.name in accepted_names), None)
        if product is None:
            product = Product(sku=sku, name=str(definition["name"]), category=definition["category"], price=definition["price"], stock=definition["stock"], description=str(definition["description"]))
            session.add(product)
            existing_products.append(product)
        else:
            product.sku = sku
            product.name = str(definition["name"])
            product.category = definition["category"]
            product.price = definition["price"]
            product.stock = definition["stock"]
            product.description = str(definition["description"])
            product.is_active = True
        seeded.append(product)

    seeded_ids = {product.id for product in seeded if product.id is not None}
    for product in existing_products:
        if product.name in _LEGACY_PRODUCT_NAMES and product.id not in seeded_ids:
            product.is_active = False
    await session.flush()
    demo_skus = [str(product["sku"]) for product in PRODUCTS]
    result = await session.execute(
        sa_select(Product).where(Product.sku.in_(demo_skus)).order_by(Product.sku)
    )
    return list(result.scalars().all())


async def seed_orders(session: AsyncSession, users: dict, products: list[Product]) -> None:
    from sqlalchemy import select as sa_select

    customer = users.get(_DEMO_CUST_EMAIL)
    if customer is None:
        return
    product_map = {p.name: p for p in products}

    orders_to_seed = [
        ("ORD-000001", "Aurora Buds Pro 无线降噪耳机", OrderStatus.DELIVERED.value, 2,
         timedelta(days=5), timedelta(days=4), timedelta(days=3), timedelta(days=7)),
        ("ORD-000002", "FlowKeys 机械键盘", OrderStatus.PAID.value, 1,
         timedelta(hours=1), None, None, timedelta(hours=3)),
        ("ORD-000003", "Halo Monitor 智能屏幕挂灯", OrderStatus.SHIPPED.value, 1,
         timedelta(days=1), timedelta(hours=12), None, timedelta(days=2)),
    ]

    for order_num, pname, status, qty, paid_delta, ship_delta, deliv_delta, create_delta in orders_to_seed:
        result = await session.execute(
            sa_select(Order).where(Order.order_number == order_num)
        )
        order = result.scalar_one_or_none()
        if order is None:
            p = product_map[pname]
            now = datetime.now(UTC)
            order = Order(
                user_id=customer.id, order_number=order_num, status=status,
                total_amount=p.price * qty, shipping_address="Demo Address",
                shipping_fee=Decimal("0"), paid_amount=p.price * qty,
                paid_at=now - paid_delta,
                shipped_at=now - ship_delta if ship_delta else None,
                delivered_at=now - deliv_delta if deliv_delta else None,
                created_at=now - create_delta,
            )
            session.add(order)
            await session.flush()
            session.add(OrderItem(
                order_id=order.id, product_id=p.id, product_name=p.name,
                unit_price=p.price, quantity=qty, subtotal=p.price * qty,
            ))
            await session.flush()

        # Backfill logistics for shipped and delivered demo orders.
        if status in {OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value}:
            log_exists = await session.execute(
                sa_text("SELECT 1 FROM logistics_records WHERE order_id = :oid"),
                {"oid": order.id},
            )
            if log_exists.scalar() is None:
                delivered = status == OrderStatus.DELIVERED.value
                session.add(LogisticsRecord(
                    order_id=order.id,
                    tracking_number=f"SF{order_num.removeprefix('ORD-'):0>11}",
                    carrier="顺丰速运",
                    status=(
                        LogisticsStatus.DELIVERED.value
                        if delivered else LogisticsStatus.IN_TRANSIT.value
                    ),
                    current_location="已签收" if delivered else "上海分拨中心",
                    actual_delivery=order.delivered_at if delivered else None,
                    events=[],
                ))
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
    result = await session.execute(
        sa_select(AgentSession.id)
        .where(AgentSession.user_id == customer.id)
        .limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return  # Already seeded

    sess = AgentSession(user_id=customer.id, status="ACTIVE", message_count=2)
    session.add(sess)
    await session.flush()
    session.add(AgentMessage(session_id=sess.id, turn_id=sess.id, role=MessageRole.USER.value, content="你好，我想查询订单物流。", sequence_number=1, turn_sequence=0))
    session.add(AgentMessage(session_id=sess.id, turn_id=sess.id, role=MessageRole.ASSISTANT.value, content="订单 ORD-000003 正在运输中。", sequence_number=2, turn_sequence=1))
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
        print(f"  Demo Customer configured: {_DEMO_CUST_EMAIL}")
        print(f"  Demo Admin configured:    {_DEMO_ADMIN_EMAIL}")


if __name__ == "__main__":
    asyncio.run(main())
