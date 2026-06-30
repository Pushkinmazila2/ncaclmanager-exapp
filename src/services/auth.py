"""
Хелперы авторизации для ExApp.
AppAPI передаёт пользователя в заголовках NC-USER и NC-USER-GROUPS.
"""

from fastapi import Request
from src.models.settings import AdminGroupsSettings
from src.services import db


def get_nc_user(request: Request) -> str:
    """SAM/uid текущего пользователя NC из заголовка."""
    return (
        request.headers.get("NC-USER")
        or request.headers.get("X-Nc-User")
        or ""
    )


def get_nc_groups(request: Request) -> str:
    """Группы пользователя NC (comma-separated) из заголовка."""
    return (
        request.headers.get("NC-USER-GROUPS")
        or request.headers.get("X-Nc-User-Groups")
        or ""
    )


async def is_acl_admin(request: Request) -> bool:
    """
    Проверяет является ли пользователь ACL-администратором.
    1. Входит в admin_groups (AD группы синхронизированные в NC)
    2. Входит в nc_admin_users (только Test режим)
    """
    settings = await db.get_settings()
    groups_cfg: AdminGroupsSettings = settings.groups
    agent_mode = settings.agent_mode.lower()

    user   = get_nc_user(request)
    groups = [g.strip() for g in get_nc_groups(request).split(",") if g.strip()]

    # Проверка по AD группам
    for admin_group in groups_cfg.admin_groups:
        if admin_group in groups:
            return True

    # Проверка по NC пользователям (только Test режим)
    if agent_mode == "test" and user in groups_cfg.nc_admin_users:
        return True

    return False


async def require_acl_admin(request: Request) -> str:
    """Dependency: возвращает uid или кидает 403."""
    from fastapi import HTTPException
    if not await is_acl_admin(request):
        raise HTTPException(status_code=403, detail="Недостаточно прав ACL")
    return get_nc_user(request)
