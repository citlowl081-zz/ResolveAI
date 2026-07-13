"""Unit tests for common Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.common import APIResponse, PaginatedResponse, Pagination


def test_api_response_success() -> None:
    """APIResponse with success=True wraps data correctly."""
    resp = APIResponse[str](success=True, code="OK", message="Done", data="hello")
    assert resp.success is True
    assert resp.code == "OK"
    assert resp.data == "hello"


def test_api_response_error() -> None:
    """APIResponse with success=False has null data."""
    resp = APIResponse[str](success=False, code="NOT_FOUND", message="Missing", data=None)
    assert resp.success is False
    assert resp.data is None


def test_api_response_serialization() -> None:
    """APIResponse serializes to dict correctly."""
    resp = APIResponse[str](success=True, code="OK", data="test")
    d = resp.model_dump()
    assert d["success"] is True
    assert d["code"] == "OK"
    assert d["data"] == "test"


def test_pagination_valid() -> None:
    """Pagination with valid fields passes validation."""
    p = Pagination(total=100, page=1, page_size=20, total_pages=5)
    assert p.total == 100
    assert p.page == 1


def test_pagination_invalid_negative_total() -> None:
    """Pagination rejects negative total."""
    with pytest.raises(ValidationError):
        Pagination(total=-1, page=1, page_size=20, total_pages=0)


def test_paginated_response() -> None:
    """PaginatedResponse wraps items with pagination metadata."""
    p = Pagination(total=2, page=1, page_size=10, total_pages=1)
    resp = PaginatedResponse[str](items=["a", "b"], pagination=p)
    assert len(resp.items) == 2
    assert resp.pagination.total == 2
