"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_after_sales,
    admin_agent,
    admin_reshipments,
    after_sales,
    agent,
    auth,
    logistics,
    orders,
    products,
)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth.router)
v1_router.include_router(products.router)
v1_router.include_router(orders.router)
v1_router.include_router(logistics.router)
v1_router.include_router(after_sales.router)
v1_router.include_router(agent.router)
v1_router.include_router(admin.router)
v1_router.include_router(admin_after_sales.router)
v1_router.include_router(admin_reshipments.router)
v1_router.include_router(admin_agent.router)
