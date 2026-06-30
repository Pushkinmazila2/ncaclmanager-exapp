import logging
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from src.models.settings import AgentSettings, AdminGroupsSettings, PathMapping
from src.services import db, agent as agent_svc
from src.services.auth import get_nc_user, get_nc_groups

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings")


class SaveSettingsRequest(BaseModel):
    agent_url:          Optional[str]       = None
    bearer_token:       Optional[str]       = None
    client_cert:        Optional[str]       = None
    cert_password:      Optional[str]       = None
    timeout:            Optional[int]       = None
    verify_ssl:         Optional[bool]      = None
    admin_groups:       Optional[list[str]] = None
    nc_admin_users:     Optional[list[str]] = None
    owner_mode_enabled: Optional[bool]      = None


class SaveMappingsRequest(BaseModel):
    mounts: list[PathMapping]


@router.get("")
async def get_settings(request: Request):
    s = await db.get_settings()
    return {
        "agent_url":          s.agent.agent_url,
        "bearer_token_set":   bool(s.agent.bearer_token),
        "client_cert":        s.agent.client_cert,
        "timeout":            s.agent.timeout,
        "verify_ssl":         s.agent.verify_ssl,
        "admin_groups":       s.groups.admin_groups,
        "nc_admin_users":     s.groups.nc_admin_users,
        "owner_mode_enabled": s.groups.owner_mode,
        "agent_mode":         s.agent_mode,
        # Роль текущего пользователя
        "is_admin":           await _is_admin(request, s),
    }


@router.post("")
async def save_settings(body: SaveSettingsRequest, request: Request):
    s = await db.get_settings()

    # Обновляем настройки агента
    agent_update = s.agent.model_dump()
    if body.agent_url    is not None: agent_update["agent_url"]    = body.agent_url
    if body.client_cert  is not None: agent_update["client_cert"]  = body.client_cert
    if body.timeout      is not None: agent_update["timeout"]      = body.timeout
    if body.verify_ssl   is not None: agent_update["verify_ssl"]   = body.verify_ssl
    if body.bearer_token:             agent_update["bearer_token"] = body.bearer_token
    if body.cert_password:            agent_update["cert_password"] = body.cert_password

    await db.save_agent_settings(AgentSettings(**agent_update))

    # Обновляем группы
    groups_update = s.groups.model_dump()
    if body.admin_groups       is not None: groups_update["admin_groups"]   = body.admin_groups
    if body.nc_admin_users     is not None: groups_update["nc_admin_users"] = body.nc_admin_users
    if body.owner_mode_enabled is not None: groups_update["owner_mode"]     = body.owner_mode_enabled

    await db.save_groups_settings(AdminGroupsSettings(**groups_update))

    logger.info("Настройки сохранены пользователем: %s", get_nc_user(request))
    return {"success": True}


@router.post("/test-agent")
async def test_agent(body: SaveSettingsRequest, request: Request):
    """
    Тест соединения с агентом.
    Принимает текущие значения формы — не требует предварительного сохранения.
    """
    s = await db.get_settings()

    # Используем параметры из запроса, fallback на сохранённые
    test_settings = AgentSettings(
        agent_url    = body.agent_url    or s.agent.agent_url,
        bearer_token = body.bearer_token or s.agent.bearer_token,
        client_cert  = body.client_cert  or s.agent.client_cert,
        cert_password = body.cert_password or s.agent.cert_password,
        timeout      = body.timeout      or s.agent.timeout,
        verify_ssl   = body.verify_ssl   if body.verify_ssl is not None else s.agent.verify_ssl,
    )

    user   = get_nc_user(request)
    groups = get_nc_groups(request)

    diagnostics = {
        "agent_url":    test_settings.agent_url    or "(не задан)",
        "bearer_token": _mask(test_settings.bearer_token),
        "client_cert":  test_settings.client_cert  or "(не задан)",
        "cert_exists":  bool(test_settings.client_cert),
        "cert_password": _mask(test_settings.cert_password),
        "timeout":      test_settings.timeout,
        "verify_ssl":   test_settings.verify_ssl,
        "current_user": user or "(не задан)",
        "user_groups":  groups or "(не задан)",
    }

    curl = _build_curl(test_settings)

    try:
        result = await agent_svc.health_check(test_settings)

        # Кэшируем режим агента
        mode = result.get("mode", "")
        if mode:
            await db.save_agent_mode(mode)

        return {
            "success":      True,
            "result":       result,
            "diagnostics":  diagnostics,
            "curl_command": curl,
            "agent_mode":   mode,
        }
    except Exception as e:
        logger.error("testAgent error: %s", e)
        return {
            "success":      False,
            "error":        str(e),
            "diagnostics":  diagnostics,
            "curl_command": curl,
            "agent_mode":   None,
        }


@router.post("/upload-cert")
async def upload_cert(file: UploadFile = File(...)):
    """Загрузка PFX сертификата через браузер."""
    import os

    if not file.filename or not file.filename.lower().endswith((".pfx", ".p12")):
        raise HTTPException(400, "Допустимы только файлы .pfx или .p12")

    cert_dir  = "/data/certs"
    cert_path = f"{cert_dir}/client.pfx"
    os.makedirs(cert_dir, exist_ok=True)

    content = await file.read()
    with open(cert_path, "wb") as f:
        f.write(content)

    # Сохраняем путь
    s = await db.get_settings()
    agent_update = s.agent.model_dump()
    agent_update["client_cert"] = cert_path
    await db.save_agent_settings(AgentSettings(**agent_update))

    logger.info("Сертификат загружен: %s (%d bytes)", cert_path, len(content))
    return {"success": True, "cert_path": cert_path, "size": len(content)}


@router.get("/nc-users")
async def search_nc_users(q: str = ""):
    """
    Поиск NC пользователей для добавления в nc_admin_users.
    В ExApp контексте используем nc-py-api для поиска.
    """
    if len(q) < 2:
        return {"users": []}

    try:
        from nc_py_api import Nextcloud
        nc = _get_nc_client()
        users = nc.users.get_list(search=q, limit=20)
        result = [
            {
                "uid":         u,
                "displayName": u,
                "email":       "",
            }
            for u in users
        ]
        return {"users": result}
    except Exception as e:
        logger.warning("nc-users search error: %s", e)
        return {"users": []}


# ── Маппинги ──────────────────────────────────────────────────────────

@router.get("/mounts")
async def get_mounts():
    s = await db.get_settings()
    return {"mounts": [m.model_dump() for m in s.mappings]}


@router.post("/mounts")
async def save_mounts(body: SaveMappingsRequest, request: Request):
    # Валидируем UNC пути
    for m in body.mounts:
        if not m.unc_path.startswith("\\\\") and not m.unc_path.startswith("//"):
            raise HTTPException(400, f"UNC путь должен начинаться с \\\\: {m.unc_path}")

    await db.save_mappings(body.mounts)
    logger.info("Маппинги сохранены: %d штук", len(body.mounts))
    return {"success": True, "count": len(body.mounts)}


# ── Утилиты ───────────────────────────────────────────────────────────

def _mask(s: str) -> str:
    if not s: return "(не задан)"
    if len(s) <= 6: return "*" * len(s)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def _build_curl(s: AgentSettings) -> str:
    lines = [
        f"curl -v \\",
        f"  --cert '{s.client_cert}' --cert-type P12 \\",
        f"  --pass '{_mask(s.cert_password)}' \\",
        f"  -H 'Authorization: Bearer {_mask(s.bearer_token)}' \\",
        f"  -H 'Accept: application/json' \\",
        f"  {'--insecure' if not s.verify_ssl else ''} \\",
        f"  -X GET '{s.agent_url.rstrip('/')}/api/acl/health'",
    ]
    return "\n".join(lines)


async def _is_admin(request: Request, s) -> bool:
    from src.services.auth import get_nc_user, get_nc_groups
    user   = get_nc_user(request)
    groups = [g.strip() for g in get_nc_groups(request).split(",") if g.strip()]
    for ag in s.groups.admin_groups:
        if ag in groups:
            return True
    if s.agent_mode.lower() == "test" and user in s.groups.nc_admin_users:
        return True
    return False


def _get_nc_client():
    """Создаём NC клиент из переменных окружения."""
    import os
    from nc_py_api import Nextcloud
    return Nextcloud(
        nextcloud_url=os.environ["NEXTCLOUD_URL"],
        nc_auth_user=os.environ.get("APP_ID", "ncaclmanager"),
        nc_auth_pass=os.environ.get("APP_SECRET", ""),
    )
