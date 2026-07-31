"""Tests for pytest database safety checks."""

import pytest

from app.database.test_guard import assert_safe_test_database_url


def test_accepts_database_name_ending_in_test() -> None:
    assert_safe_test_database_url(
        "postgresql+asyncpg://test-user:test-only@localhost:5433/resolveai_test"
    )


@pytest.mark.parametrize("database_name", ["resolveai", "resolveai_uat", "production"])
def test_rejects_non_test_database(database_name: str) -> None:
    with pytest.raises(RuntimeError, match="database name must end with '_test'"):
        assert_safe_test_database_url(
            f"postgresql+asyncpg://test-user:test-only@localhost:5433/{database_name}"
        )


def test_rejects_invalid_database_url_without_leaking_it() -> None:
    unsafe_value = "not a database URL with a private token"
    with pytest.raises(RuntimeError) as caught:
        assert_safe_test_database_url(unsafe_value)
    assert unsafe_value not in str(caught.value)
