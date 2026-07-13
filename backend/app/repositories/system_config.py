"""SystemConfigRepository."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig
from app.repositories.base import BaseRepository


class SystemConfigRepository(BaseRepository):
    model = SystemConfig

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_key(self, key: str) -> SystemConfig | None:
        result = await self.session.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        return result.scalar_one_or_none()

    async def upsert(self, key: str, value: dict, description: str | None = None) -> SystemConfig:
        stmt = (
            pg_insert(SystemConfig)
            .values(config_key=key, config_value=value, description=description)
            .on_conflict_do_update(
                index_elements=["config_key"],
                set_={"config_value": value, "description": description},
            )
            .returning(SystemConfig.id)
        )
        result = await self.session.execute(stmt)
        row = result.fetchone()
        await self.session.flush()
        config = await self.get_by_id(row.id) if row else None
        return config  # type: ignore[return-value]
