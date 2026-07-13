"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, logistics, orders, products

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth.router)
v1_router.include_router(products.router)
v1_router.include_router(orders.router)
v1_router.include_router(logistics.router)
v1_router.include_router(admin.router)
