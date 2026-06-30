"""
Хранилище настроек в SQLite.
Файл БД монтируется как Docker volume для persistence.
"""

import json
import os
import aiosqlite
from src.models.settings import FullSettings, AgentSettings, AdminGroupsSettings, PathMapping


def _db_path() -> str:
    """Читаем переменную окружения динамически — не на момент импорта модуля."""
    return os.environ.get("DB_PATH", "/data/ncaclmanager.db")


async def init_db() -> None:
    db_path = _db_path()
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        await db.commit()


async def get_settings() -> FullSettings:
    async with aiosqlite.connect(_db_path()) as db:
        async with db.execute("SELECT key, value FROM settings") as cur:
            rows = await cur.fetchall()

    data = {row[0]: json.loads(row[1]) for row in rows}

    agent = AgentSettings(**data.get("agent", {}))
    groups = AdminGroupsSettings(**data.get("groups", {}))
    mappings_raw = data.get("mappings", [])
    mappings = [PathMapping(**m) for m in mappings_raw]
    agent_mode = data.get("agent_mode", "")

    return FullSettings(
        agent=agent,
        groups=groups,
        mappings=mappings,
        agent_mode=agent_mode,
    )


async def save_agent_settings(settings: AgentSettings) -> None:
    """Сохраняем настройки агента. Пустые секреты не перезаписываем."""
    current = await get_settings()

    # Не перезаписываем секреты если пришли пустыми
    if not settings.bearer_token:
        settings = settings.model_copy(update={"bearer_token": current.agent.bearer_token})
    if not settings.cert_password:
        settings = settings.model_copy(update={"cert_password": current.agent.cert_password})

    await _set("agent", settings.model_dump())


async def save_groups_settings(groups: AdminGroupsSettings) -> None:
    await _set("groups", groups.model_dump())


async def save_mappings(mappings: list[PathMapping]) -> None:
    await _set("mappings", [m.model_dump() for m in mappings])


async def save_agent_mode(mode: str) -> None:
    await _set("agent_mode", mode)


async def _set(key: str, value) -> None:
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value, ensure_ascii=False))
        )
        await db.commit()
