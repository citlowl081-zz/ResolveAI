"""search_after_sales_policy — search the RAG policy knowledge base (CUSTOMER only)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.settings import settings
from app.models.enums import UserRole
from app.rag.embeddings import build_embedding_provider
from app.services.policy_service import PolicyService
from app.tools.base import BaseTool, ToolContract


class SearchAfterSalesPolicyTool(BaseTool):
    contract = ToolContract(
        tool_name="search_after_sales_policy",
        description=(
            "Search the after-sales policy knowledge base for policies "
            "relevant to a customer's issue. Returns matching policy "
            "titles, summaries, and relevant text snippets with similarity scores."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query describing the issue",
                },
                "category": {
                    "type": "string",
                    "description": "Optional policy category filter (RETURN, REFUND, EXCHANGE, RESHIPMENT, LOGISTICS, RISK, SOP, GENERAL)",
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Maximum number of results to return",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        allowed_roles={UserRole.CUSTOMER},
        is_mutating=False,
        audit_action="search_policy",
        underlying_service="PolicyService",
        possible_error_codes=["TOOL_TIMEOUT", "TOOL_EXECUTION_FAILED"],
    )

    async def execute(
        self,
        session: AsyncSession,
        tool_input: dict,
        user_id: uuid.UUID,
    ) -> dict:
        query = tool_input["query"]
        category = tool_input.get("category")
        top_k = tool_input.get("top_k", 5)

        bind = session.get_bind()
        factory = async_sessionmaker(bind, class_=AsyncSession, expire_on_commit=False)  # type: ignore[call-overload]
        provider = build_embedding_provider()
        svc = PolicyService(session_factory=factory, embedding_provider=provider)

        results = await svc.search(
            query=query,
            top_k=top_k,
            category=category,
            min_similarity=settings.rag_min_similarity,
        )

        return {"policies": results}
