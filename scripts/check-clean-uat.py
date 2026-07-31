"""Report non-sensitive acceptance statistics for the clean UAT database."""

import json
import os
import urllib.error
import urllib.request

import psycopg2


def _login_status(email_env: str, password_env: str) -> bool:
    payload = json.dumps({
        "email": os.environ[email_env],
        "password": os.environ[password_env],
    }).encode()
    request = urllib.request.Request(
        "http://localhost:8000/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def main() -> None:
    database_url = os.environ["DATABASE_URL"].replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )
    with psycopg2.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*), COUNT(DISTINCT sku), "
            "COUNT(DISTINCT split_part(sku, '-', 2)) "
            "FROM products WHERE is_active = TRUE AND sku LIKE 'RA-%'"
        )
        products, distinct_skus, categories = cursor.fetchone()
        cursor.execute(
            "SELECT COUNT(*) FROM (SELECT sku FROM products WHERE sku IS NOT NULL "
            "GROUP BY sku HAVING COUNT(*) > 1) duplicates"
        )
        duplicate_skus = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM policy_documents WHERE status = 'ACTIVE'")
        active_policies = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM (SELECT policy_key, version FROM policy_documents "
            "WHERE status = 'ACTIVE' GROUP BY policy_key, version HAVING COUNT(*) > 1) d"
        )
        duplicate_policies = cursor.fetchone()[0]

    print(f"UAT categories: {categories}")
    print(f"UAT products: {products}")
    print(f"UAT distinct SKU: {distinct_skus}")
    print(f"UAT duplicate SKU groups: {duplicate_skus}")
    print(f"UAT ACTIVE policies: {active_policies}")
    print(f"UAT duplicate ACTIVE policy key/version: {duplicate_policies}")
    print(f"Demo Customer login: {'PASS' if _login_status('DEMO_CUSTOMER_EMAIL', 'DEMO_CUSTOMER_PASSWORD') else 'FAIL'}")
    print(f"Demo Admin login: {'PASS' if _login_status('DEMO_ADMIN_EMAIL', 'DEMO_ADMIN_PASSWORD') else 'FAIL'}")


if __name__ == "__main__":
    main()
