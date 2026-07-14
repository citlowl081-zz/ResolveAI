"""IdempotencyService — INSERT ON CONFLICT DO NOTHING RETURNING pattern."""

import hashlib
import json
import uuid
from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError
from app.repositories.idempotency import IdempotencyRepository


def compute_request_hash(
    method: str,
    path: str,
    path_params: dict[str, str],
    query_params: dict[str, str],
    body: dict | None,
) -> str:
    """Compute SHA-256 hash of a canonical request representation."""
    sorted_path = "&".join(f"{k}={v}" for k, v in sorted(path_params.items()))
    sorted_query = "&".join(f"{k}={v}" for k, v in sorted(query_params.items()))
    query_str = f"?{sorted_query}" if sorted_query else ""
    body_str = json.dumps(body or {}, sort_keys=True, separators=(",", ":"))
    canonical = f"{method}|{path}|{sorted_path}|{query_str}|{body_str}"
    return hashlib.sha256(canonical.encode()).hexdigest()


class IdempotencyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IdempotencyRepository(session)

    async def acquire_or_get_cached(
        self,
        user_id: uuid.UUID,
        operation: str,
        idempotency_key: str,
        request_hash: str,
    ) -> dict | None:
        """Try to acquire the idempotency slot.

        Returns None → proceed with business logic (this request won).
        Returns dict → return cached response (this is a replay).
        Raises ConflictError → hash mismatch or request in progress.
        """
        record, is_new = await self.repo.acquire_or_get(
            user_id, operation, idempotency_key, request_hash,
        )

        if is_new:
            return None  # Winner — proceed

        # Conflict — another request exists. Lock and inspect.
        record = await self.repo.get_for_update(user_id, operation, idempotency_key)
        if record is None:
            # Race: the other request just committed and the row is gone.
            # Retry acquisition.
            record2, is_new2 = await self.repo.acquire_or_get(
                user_id, operation, idempotency_key, request_hash,
            )
            if is_new2:
                return None  # Winner on retry
            record = await self.repo.get_for_update(user_id, operation, idempotency_key)

        if record is None:
            raise ConflictError("Idempotency conflict; please retry")

        if record.status == "COMPLETED":
            if record.request_hash == request_hash:
                return {
                    "status": record.response_status,
                    "body": record.response_body,
                }
            raise ConflictError("Idempotency key reused with different request")

        if record.status == "PROCESSING":
            from datetime import datetime
            if record.expires_at and record.expires_at <= datetime.now(UTC):
                # Expired — reset and proceed
                await self.repo.reset_expired(record.id, request_hash)
                return None
            raise ConflictError("A request with this idempotency key is currently processing")

        raise ConflictError("Unexpected idempotency state")

    async def complete(
        self,
        user_id: uuid.UUID,
        operation: str,
        idempotency_key: str,
        response_status: int,
        response_body: dict | None = None,
        resource_id: uuid.UUID | None = None,
    ) -> None:
        record = await self.repo.get_for_update(user_id, operation, idempotency_key)
        if record is not None:
            await self.repo.complete(record.id, response_status, response_body, resource_id)

    async def bind_resource(
        self,
        user_id: uuid.UUID,
        operation: str,
        idempotency_key: str,
        resource_id: uuid.UUID,
    ) -> bool:
        """Early-bind a resource_id to a PROCESSING idempotency record.

        Only succeeds when the record is PROCESSING and the resource_id is
        not already bound to a different value.
        Returns True if binding was applied.
        """
        record = await self.repo.get_for_update(user_id, operation, idempotency_key)
        if record is None:
            return False
        return await self.repo.bind_resource(record.id, resource_id)
