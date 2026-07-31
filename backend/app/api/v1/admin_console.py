"""Read-only, privacy-safe API for the administration console."""

import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database.session import get_db
from app.exceptions import NotFoundError
from app.models.after_sales_ticket import AfterSalesTicket
from app.models.agent_session import AgentSession
from app.models.agent_tool_log import AgentToolLog
from app.models.approval_task import ApprovalTask
from app.models.customer_memory import CustomerMemory
from app.models.enums import ApprovalStatus, OrderStatus, PolicyStatus, TicketStatus, UserRole
from app.models.logistics_record import LogisticsRecord
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.policy_document import PolicyDocument
from app.models.user import User
from app.schemas.admin_console import AdminPage, DashboardMetrics, SystemStatus
from app.schemas.common import APIResponse
from app.security.dependencies import require_role

router = APIRouter(prefix="/admin/console", tags=["admin-console"])
admin_only = Depends(require_role("OPERATOR", "ADMIN"))


def _enum(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _page(items: list[dict[str, Any]], total: int, page: int, page_size: int) -> AdminPage:
    return AdminPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/dashboard")
async def dashboard(
    days: int = Query(7, ge=7, le=30),
    current_user: dict = admin_only,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DashboardMetrics]:
    """Return only metrics calculated from the current database."""
    now = datetime.now(UTC)
    start = now - timedelta(days=days - 1)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async def count(statement: Any) -> int:
        return int((await db.execute(statement)).scalar_one())

    pending = await count(select(func.count()).select_from(AfterSalesTicket).where(
        AfterSalesTicket.status == TicketStatus.NEEDS_REVIEW,
    ))
    today_count = await count(select(func.count()).select_from(AfterSalesTicket).where(
        AfterSalesTicket.created_at >= today,
    ))
    approvals = await count(select(func.count()).select_from(ApprovalTask).where(
        ApprovalTask.status == ApprovalStatus.PENDING,
    ))
    sessions = await count(select(func.count()).select_from(AgentSession).where(
        AgentSession.created_at >= start,
    ))
    searches = await count(select(func.count()).select_from(AgentToolLog).where(
        AgentToolLog.tool_name == "search_after_sales_policy",
        AgentToolLog.created_at >= start,
    ))
    failures = await count(select(func.count()).select_from(AgentToolLog).where(
        AgentToolLog.is_success.is_(False), AgentToolLog.created_at >= start,
    ))

    trend_rows = (await db.execute(
        select(func.date(AfterSalesTicket.created_at), func.count())
        .where(AfterSalesTicket.created_at >= start)
        .group_by(func.date(AfterSalesTicket.created_at))
        .order_by(func.date(AfterSalesTicket.created_at))
    )).all()
    status_rows = (await db.execute(
        select(AfterSalesTicket.status, func.count()).group_by(AfterSalesTicket.status)
    )).all()
    intent_rows = (await db.execute(
        select(AfterSalesTicket.intent, func.count()).group_by(AfterSalesTicket.intent)
    )).all()
    high_risk = (await db.execute(
        select(ApprovalTask).where(ApprovalTask.risk_level.in_(["HIGH", "CRITICAL"]))
        .order_by(desc(ApprovalTask.created_at)).limit(5)
    )).scalars().all()
    failed_tools = (await db.execute(
        select(AgentToolLog).where(AgentToolLog.is_success.is_(False))
        .order_by(desc(AgentToolLog.created_at)).limit(5)
    )).scalars().all()

    metrics = DashboardMetrics(
        range_days=days,
        pending_tickets=pending,
        today_tickets=today_count,
        pending_approvals=approvals,
        agent_sessions=sessions,
        policy_searches=searches,
        failed_tool_calls=failures,
        ticket_trend=[{"date": str(day), "count": value} for day, value in trend_rows],
        ticket_statuses=[{"status": _enum(status), "count": value} for status, value in status_rows],
        intent_types=[{"intent": _enum(intent), "count": value} for intent, value in intent_rows],
        recent_high_risk_approvals=[{
            "id": str(item.id), "tool_name": item.tool_name, "risk_level": item.risk_level,
            "status": _enum(item.status), "created_at": _iso(item.created_at),
        } for item in high_risk],
        recent_failed_tools=[{
            "id": str(item.id), "tool_name": item.tool_name, "error_code": item.error_code,
            "duration_ms": item.duration_ms, "created_at": _iso(item.created_at),
        } for item in failed_tools],
    )
    return APIResponse(success=True, code="OK", data=metrics)


@router.get("/orders")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    query: str | None = Query(None, max_length=100),
    status: OrderStatus | None = Query(None),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    current_user: dict = admin_only,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AdminPage]:
    filters = []
    if query:
        filters.append(or_(Order.order_number.ilike(f"%{query}%"), User.full_name.ilike(f"%{query}%")))
    if status:
        filters.append(Order.status == status)
    base = select(Order, User).join(User, User.id == Order.user_id).where(*filters)
    total = int((await db.execute(
        select(func.count()).select_from(Order).join(User, User.id == Order.user_id).where(*filters)
    )).scalar_one())
    ordering = Order.created_at.asc() if sort_order == "asc" else desc(Order.created_at)
    rows = (await db.execute(base.order_by(ordering).offset((page - 1) * page_size).limit(page_size))).all()
    items: list[dict[str, Any]] = []
    for order, user in rows:
        names = (await db.execute(select(OrderItem.product_name).where(OrderItem.order_id == order.id).limit(3))).scalars().all()
        logistics = (await db.execute(select(LogisticsRecord).where(LogisticsRecord.order_id == order.id))).scalar_one_or_none()
        ticket_count = int((await db.execute(select(func.count()).select_from(AfterSalesTicket).where(AfterSalesTicket.order_id == order.id))).scalar_one())
        items.append({
            "id": str(order.id), "order_number": order.order_number, "user_id": str(user.id),
            "user_name": user.full_name, "item_summary": "、".join(names), "paid_amount": str(order.paid_amount),
            "status": _enum(order.status), "logistics_status": _enum(logistics.status) if logistics else None,
            "ticket_count": ticket_count, "created_at": _iso(order.created_at),
        })
    return APIResponse(success=True, code="OK", data=_page(items, total, page, page_size))


@router.get("/orders/{order_id}")
async def get_order(
    order_id: uuid.UUID,
    current_user: dict = admin_only,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, Any]]:
    row = (await db.execute(select(Order, User).join(User, User.id == Order.user_id).where(Order.id == order_id))).one_or_none()
    if row is None:
        raise NotFoundError("Order not found")
    order, user = row
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
    logistics = (await db.execute(select(LogisticsRecord).where(LogisticsRecord.order_id == order.id))).scalar_one_or_none()
    tickets = (await db.execute(select(AfterSalesTicket).where(AfterSalesTicket.order_id == order.id).order_by(desc(AfterSalesTicket.created_at)))).scalars().all()
    return APIResponse(success=True, code="OK", data={
        "id": str(order.id), "order_number": order.order_number, "user_id": str(user.id),
        "user_name": user.full_name, "status": _enum(order.status), "total_amount": str(order.total_amount),
        "discount_amount": str(order.discount_amount), "paid_amount": str(order.paid_amount),
        "shipping_fee": str(order.shipping_fee), "paid_at": _iso(order.paid_at),
        "shipped_at": _iso(order.shipped_at), "delivered_at": _iso(order.delivered_at),
        "created_at": _iso(order.created_at),
        "items": [{"id": str(i.id), "product_id": str(i.product_id), "product_name": i.product_name,
                   "unit_price": str(i.unit_price), "quantity": i.quantity, "subtotal": str(i.subtotal)} for i in items],
        "logistics": None if logistics is None else {"status": _enum(logistics.status), "carrier": logistics.carrier,
                                                       "tracking_number": logistics.tracking_number,
                                                       "current_location": logistics.current_location},
        "tickets": [{"id": str(t.id), "ticket_number": t.ticket_number, "intent": _enum(t.intent),
                     "status": _enum(t.status), "created_at": _iso(t.created_at)} for t in tickets],
    })


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    query: str | None = Query(None, max_length=100),
    role: UserRole | None = Query(None),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    current_user: dict = admin_only,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[AdminPage]:
    filters = []
    if query:
        filters.append(or_(User.full_name.ilike(f"%{query}%"), User.email.ilike(f"%{query}%")))
    if role:
        filters.append(User.role == role)
    total = int((await db.execute(select(func.count()).select_from(User).where(*filters))).scalar_one())
    ordering = User.created_at.asc() if sort_order == "asc" else desc(User.created_at)
    users = (await db.execute(select(User).where(*filters).order_by(ordering).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    items: list[dict[str, Any]] = []
    for user in users:
        order_count = int((await db.execute(select(func.count()).select_from(Order).where(Order.user_id == user.id))).scalar_one())
        ticket_count = int((await db.execute(select(func.count()).select_from(AfterSalesTicket).where(AfterSalesTicket.user_id == user.id))).scalar_one())
        memory_count = int((await db.execute(select(func.count()).select_from(CustomerMemory).where(CustomerMemory.user_id == user.id))).scalar_one())
        items.append({"id": str(user.id), "full_name": user.full_name, "email": user.email,
                      "role": _enum(user.role), "risk_level": _enum(user.risk_level), "is_active": user.is_active,
                      "order_count": order_count, "ticket_count": ticket_count, "memory_count": memory_count,
                      "created_at": _iso(user.created_at)})
    return APIResponse(success=True, code="OK", data=_page(items, total, page, page_size))


@router.get("/users/{user_id}")
async def get_user(
    user_id: uuid.UUID,
    current_user: dict = admin_only,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict[str, Any]]:
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")
    orders = (await db.execute(select(Order).where(Order.user_id == user.id).order_by(desc(Order.created_at)).limit(5))).scalars().all()
    tickets = (await db.execute(select(AfterSalesTicket).where(AfterSalesTicket.user_id == user.id).order_by(desc(AfterSalesTicket.created_at)).limit(5))).scalars().all()
    memories = (await db.execute(select(CustomerMemory).where(CustomerMemory.user_id == user.id).order_by(desc(CustomerMemory.updated_at)).limit(5))).scalars().all()
    sessions = (await db.execute(select(AgentSession).where(AgentSession.user_id == user.id).order_by(desc(AgentSession.created_at)).limit(5))).scalars().all()
    return APIResponse(success=True, code="OK", data={
        "id": str(user.id), "full_name": user.full_name, "email": user.email,
        "role": _enum(user.role), "risk_level": _enum(user.risk_level), "is_active": user.is_active,
        "created_at": _iso(user.created_at),
        "orders": [{"id": str(o.id), "order_number": o.order_number, "status": _enum(o.status),
                    "paid_amount": str(o.paid_amount), "created_at": _iso(o.created_at)} for o in orders],
        "tickets": [{"id": str(t.id), "ticket_number": t.ticket_number, "status": _enum(t.status),
                     "intent": _enum(t.intent), "created_at": _iso(t.created_at)} for t in tickets],
        "memories": [{"id": str(m.id), "memory_type": _enum(m.memory_type), "content": m.content[:120],
                      "status": _enum(m.status), "updated_at": _iso(m.updated_at)} for m in memories],
        "sessions": [{"id": str(s.id), "status": s.status, "message_count": s.message_count,
                      "created_at": _iso(s.created_at)} for s in sessions],
    })


@router.get("/system-status")
async def system_status(
    current_user: dict = admin_only,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SystemStatus]:
    await db.execute(select(1))
    active_policies = int((await db.execute(select(func.count()).select_from(PolicyDocument).where(
        PolicyDocument.status == PolicyStatus.ACTIVE,
    ))).scalar_one())
    latest_policy = (await db.execute(select(func.max(PolicyDocument.updated_at)))).scalar_one_or_none()
    latest_failure = (await db.execute(select(func.max(AgentToolLog.created_at)).where(
        AgentToolLog.is_success.is_(False),
    ))).scalar_one_or_none()
    data = SystemStatus(
        backend="healthy", database="healthy", provider=settings.llm_provider,
        model=settings.llm_model, embedding_provider=settings.embedding_provider,
        api_key_configured=bool(settings.llm_api_key), base_url_configured=bool(settings.llm_base_url),
        active_policy_count=active_policies, latest_policy_update=_iso(latest_policy), latest_seed=None,
        latest_tool_failure=_iso(latest_failure), app_version=settings.app_version,
    )
    return APIResponse(success=True, code="OK", data=data)
