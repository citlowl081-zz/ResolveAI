"""MemoryService — business logic for long-term user memory.

Handles create, read, update, delete, merge/dedup, privacy filtering,
and audit logging for customer memory records.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models.customer_memory import CustomerMemory
from app.models.enums import MemoryStatus, MemoryType
from app.repositories.customer_memory import CustomerMemoryRepository
from app.services.audit import AuditService
from app.services.memory_privacy import sanitize_memory_content


class MemoryService:
    """Business logic for customer memory CRUD with privacy + audit.

    Every mutating operation:
    1. Validates input (privacy check, type validation)
    2. Applies the change through the repository
    3. Writes an audit log entry
    """

    def __init__(self, session: AsyncSession) -> None:
        self.repo = CustomerMemoryRepository(session)
        self.audit = AuditService(session)

    # ── Create ───────────────────────────────────────────────────────

    async def create_memory(
        self,
        user_id: uuid.UUID,
        memory_type: str,
        content: str,
        source: str = "explicit_api",
        key: str | None = None,
        structured_data: dict | None = None,
        confidence: float = 1.0,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CustomerMemory:
        """Create a new memory, or merge with an existing one if *key* is set."""
        # ── Validate type ───────────────────────────────────────────
        if memory_type not in MemoryType.__members__:
            raise ValidationError(f"无效的 memory_type: {memory_type}")

        # ── Privacy check ────────────────────────────────────────────
        reason = sanitize_memory_content(content, structured_data)
        if reason is not None:
            raise ValidationError(reason)

        # ── Dedup by key ─────────────────────────────────────────────
        if key is not None:
            existing = await self.repo.get_active_by_key(
                user_id, memory_type, key,
            )
            if existing is not None:
                return await self._merge_existing(
                    existing, content, structured_data, source, confidence,
                    ip_address, user_agent,
                )

        # ── Create new ───────────────────────────────────────────────
        memory = CustomerMemory(
            user_id=user_id,
            memory_type=MemoryType(memory_type),
            key=key,
            content=content,
            structured_data=structured_data,
            source=source,
            confidence=confidence,
            status=MemoryStatus.ACTIVE,
        )
        await self.repo.create(memory)

        await self.audit.log(
            user_id=user_id,
            action="CREATE_MEMORY",
            resource_type="customer_memory",
            resource_id=memory.id,
            changes={
                "memory_type": memory_type,
                "key": key,
                "content_preview": content[:200],
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return memory

    # ── Read ─────────────────────────────────────────────────────────

    async def get_memory(
        self, memory_id: uuid.UUID, user_id: uuid.UUID,
    ) -> CustomerMemory:
        """Get a single memory, scoped to *user_id*."""
        memory = await self.repo.get_by_id_and_user(memory_id, user_id)
        if memory is None:
            raise NotFoundError("Memory not found")
        return memory

    async def list_memories(
        self,
        user_id: uuid.UUID,
        memory_type: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CustomerMemory], int]:
        """List a user's memories with optional filters."""
        if memory_type is not None and memory_type not in MemoryType.__members__:
            raise ValidationError(f"无效的 memory_type: {memory_type}")
        if status is not None and status not in MemoryStatus.__members__:
            raise ValidationError(f"无效的 status: {status}")

        return await self.repo.list_by_user(
            user_id, memory_type=memory_type, status=status,
            page=page, page_size=page_size,
        )

    async def get_active_for_context(
        self, user_id: uuid.UUID, limit: int = 20,
    ) -> list[CustomerMemory]:
        """Get active memories for Agent context injection."""
        return await self.repo.get_active_for_context(user_id, limit=limit)

    # ── Update ───────────────────────────────────────────────────────

    async def update_memory(
        self,
        memory_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str | None = None,
        structured_data: dict | None = None,
        confidence: float | None = None,
        status: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CustomerMemory:
        """Update fields on an existing memory.  Only the owner can update."""
        memory = await self.repo.get_by_id_and_user(memory_id, user_id)
        if memory is None:
            raise NotFoundError("Memory not found")

        changes: dict = {}

        if content is not None:
            reason = sanitize_memory_content(content, None)
            if reason is not None:
                raise ValidationError(reason)
            changes["content"] = content

        if structured_data is not None:
            reason = sanitize_memory_content(memory.content, structured_data)
            if reason is not None:
                raise ValidationError(reason)
            changes["structured_data"] = structured_data

        if confidence is not None:
            changes["confidence"] = confidence

        if status is not None:
            if status not in ("ACTIVE", "ARCHIVED"):
                raise ValidationError(f"无效的 status: {status}")
            changes["status"] = MemoryStatus(status)

        if not changes:
            return memory

        old_preview = memory.content[:200]
        updated = await self.repo.update(memory, changes)

        await self.audit.log(
            user_id=user_id,
            action="UPDATE_MEMORY",
            resource_type="customer_memory",
            resource_id=memory.id,
            changes={
                "fields_changed": list(changes.keys()),
                "old_content_preview": old_preview,
                "new_content_preview": updated.content[:200] if content else None,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return updated

    # ── Delete ───────────────────────────────────────────────────────

    async def delete_memory(
        self,
        memory_id: uuid.UUID,
        user_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Delete a memory.  Only the owner can delete."""
        memory = await self.repo.get_by_id_and_user(memory_id, user_id)
        if memory is None:
            raise NotFoundError("Memory not found")

        memory_type = memory.memory_type.value if memory.memory_type else ""
        old_preview = memory.content[:200]

        await self.repo.delete(memory)

        await self.audit.log(
            user_id=user_id,
            action="DELETE_MEMORY",
            resource_type="customer_memory",
            resource_id=memory_id,
            changes={
                "memory_type": memory_type,
                "content_preview": old_preview,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

    # ── Internal helpers ──────────────────────────────────────────────

    async def _merge_existing(
        self,
        existing: CustomerMemory,
        content: str,
        structured_data: dict | None,
        source: str,
        confidence: float,
        ip_address: str | None,
        user_agent: str | None,
    ) -> CustomerMemory:
        """Merge new data into an existing memory (update content, bump version)."""
        old_preview = existing.content[:200]
        existing.content = content
        if structured_data is not None:
            existing.structured_data = structured_data
        existing.source = source
        existing.confidence = confidence
        existing.version = (existing.version or 1) + 1
        await self.repo.update(existing, {})

        await self.audit.log(
            user_id=existing.user_id,
            action="MERGE_MEMORY",
            resource_type="customer_memory",
            resource_id=existing.id,
            changes={
                "old_content_preview": old_preview,
                "new_content_preview": content[:200],
                "new_version": existing.version,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return existing
