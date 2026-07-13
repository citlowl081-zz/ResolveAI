"""SystemConfigService."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.repositories.system_config import SystemConfigRepository


class SystemConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self.config_repo = SystemConfigRepository(session)

    async def get(self, key: str) -> dict:
        config = await self.config_repo.get_by_key(key)
        if config is None:
            raise NotFoundError(f"Config key '{key}' not found")
        return {"key": config.config_key, "value": config.config_value, "description": config.description}

    async def get_all(self) -> list[dict]:
        return []  # Simplified — Phase 02A just needs the pattern established
