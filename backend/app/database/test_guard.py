"""Safety checks for test database connections."""

from sqlalchemy.engine import make_url


def assert_safe_test_database_url(database_url: str) -> None:
    """Refuse to run tests unless the database name is explicitly test-only."""
    try:
        database_name = make_url(database_url).database or ""
    except Exception as exc:
        raise RuntimeError("TEST_DATABASE_URL is not a valid database URL") from exc
    if not database_name.lower().endswith("_test"):
        raise RuntimeError(
            "Refusing to run pytest against a non-test database; "
            "database name must end with '_test'"
        )
