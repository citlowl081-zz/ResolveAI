"""ApprovalService — create, decide, list approval tasks with audit logging."""

from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.approval_task import ApprovalTask
from app.models.enums import ApprovalStatus, ApprovalType
from app.repositories.approval_task import ApprovalTaskRepository
from app.services.audit import AuditService


class ApprovalService:
    """Business logic for human-in-the-loop approval tasks.

    Key invariants:
    - At most one PENDING approval per action_id (UNIQUE constraint + idempotent create)
    - Only PENDING tasks can be decided
    - Decisions use optimistic locking (version check)
    - All mutating operations write audit logs
    """

    def __init__(self, session: AsyncSession) -> None:
        self.repo = ApprovalTaskRepository(session)
        self.audit = AuditService(session)

    # ── Create ───────────────────────────────────────────────────────

    async def create_approval(
        self,
        *,
        user_id: uuid.UUID,
        agent_session_id: uuid.UUID | None,
        turn_id: uuid.UUID | None,
        action_id: str,
        tool_name: str,
        action_payload: dict,
        approval_types: list[str],
        risk_level: str = "LOW",
        reason: str = "",
    ) -> ApprovalTask:
        """Idempotently create an approval task for *action_id*.

        Returns the existing task if one already exists for this action_id
        (prevents duplicate approval creation on retry).
        """
        # ── Idempotency check ────────────────────────────────────────
        existing = await self.repo.get_by_action_id(action_id)
        if existing is not None:
            return existing

        # ── Determine primary approval_type ─────────────────────────
        primary_type = approval_types[0] if approval_types else "MANUAL_REQUEST"

        # Validate type
        if primary_type not in ApprovalType.__members__:
            raise ValidationError(f"无效的 approval_type: {primary_type}")

        task = ApprovalTask(
            user_id=user_id,
            agent_session_id=agent_session_id,
            turn_id=turn_id,
            action_id=action_id,
            tool_name=tool_name,
            sanitized_action_payload=action_payload,
            approval_type=ApprovalType(primary_type),
            status=ApprovalStatus.PENDING,
            risk_level=risk_level,
            reason=reason,
            requested_by=user_id,
        )
        await self.repo.create(task)

        await self.audit.log(
            user_id=user_id,
            action="APPROVAL_CREATED",
            resource_type="approval_task",
            resource_id=task.id,
            changes={
                "action_id": action_id,
                "tool_name": tool_name,
                "approval_type": primary_type,
                "risk_level": risk_level,
                "triggers": approval_types,
            },
        )

        return task

    # ── Decide ───────────────────────────────────────────────────────

    async def approve(
        self,
        task_id: uuid.UUID,
        decided_by: uuid.UUID,
        expected_version: int,
        decision_reason: str = "",
    ) -> ApprovalTask:
        """Approve a pending task. Fails on version mismatch (concurrent decision)."""
        return await self._decide(
            task_id, decided_by, expected_version,
            ApprovalStatus.APPROVED, decision_reason,
        )

    async def reject(
        self,
        task_id: uuid.UUID,
        decided_by: uuid.UUID,
        expected_version: int,
        decision_reason: str = "",
    ) -> ApprovalTask:
        """Reject a pending task. Fails on version mismatch."""
        return await self._decide(
            task_id, decided_by, expected_version,
            ApprovalStatus.REJECTED, decision_reason,
        )

    async def _decide(
        self,
        task_id: uuid.UUID,
        decided_by: uuid.UUID,
        expected_version: int,
        new_status: ApprovalStatus,
        decision_reason: str,
    ) -> ApprovalTask:
        """Execute decision with optimistic locking."""
        task = await self.repo.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Approval task not found")

        # Validate state
        current_status = task.status.value if hasattr(task.status, "value") else str(task.status)
        if current_status != "PENDING":
            raise ConflictError(
                f"Cannot {new_status.value} a task with status {current_status}. "
                f"Only PENDING tasks can be decided."
            )

        # Check expiry
        if task.expires_at and task.expires_at < dt.now(UTC):
            raise ConflictError("Cannot decide an expired task")

        updated = await self.repo.decide(
            task_id=task_id,
            expected_version=expected_version,
            new_status=new_status.value,
            decided_by=decided_by,
            decision_reason=decision_reason,
        )
        if updated is None:
            raise ConflictError(
                "Approval task was modified by another request; please retry"
            )

        action = f"APPROVAL_{new_status.value.upper()}"
        await self.audit.log(
            user_id=decided_by,
            action=action,
            resource_type="approval_task",
            resource_id=task_id,
            changes={
                "old_status": current_status,
                "new_status": new_status.value,
                "decision_reason": decision_reason,
            },
        )

        return updated

    # ── Read ─────────────────────────────────────────────────────────

    async def get_task(self, task_id: uuid.UUID) -> ApprovalTask:
        task = await self.repo.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Approval task not found")
        return task

    async def list_tasks(
        self,
        status: str | None = None,
        approval_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ApprovalTask], int]:
        """Admin view — list all approval tasks."""
        if status is not None and status not in ApprovalStatus.__members__:
            raise ValidationError(f"无效的 status: {status}")
        if approval_type is not None and approval_type not in ApprovalType.__members__:
            raise ValidationError(f"无效的 approval_type: {approval_type}")
        return await self.repo.list_pending(
            status=status, approval_type=approval_type,
            page=page, page_size=page_size,
        )

    async def list_user_tasks(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20,
    ) -> tuple[list[ApprovalTask], int]:
        """Customer view — list own approval tasks."""
        return await self.repo.list_by_user(user_id, page=page, page_size=page_size)

    async def get_task_for_user(
        self, task_id: uuid.UUID, user_id: uuid.UUID,
    ) -> ApprovalTask:
        """Get a single task, scoped to user_id."""
        task = await self.repo.get_by_id(task_id)
        if task is None or str(task.user_id) != str(user_id):
            raise NotFoundError("Approval task not found")
        return task
