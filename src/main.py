"""
NcAclManager ExApp — главная точка входа.

Регистрация в Nextcloud происходит через nc_py_api.ex_app.run_app(),
которая автоматически:
  - вызывает /heartbeat при проверках живости
  - вызывает /init при установке
  - вызывает /enabled при вкл/выкл
  - регистрирует UI элементы (sidebar, file action) через manifest API
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.routers import lifecycle, acl, groups, users, ui_actions, browse, settings as settings_router
from src.services.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ncaclmanager")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NcAclManager ExApp запускается...")
    await init_db()
    logger.info("База данных инициализирована")
    yield
    logger.info("NcAclManager ExApp остановлен")


app = FastAPI(
    title="NcAclManager ExApp",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Роутеры ───────────────────────────────────────────────────────────
app.include_router(lifecycle.router)        # /heartbeat, /init, /enabled
app.include_router(acl.router)              # /api/acl
app.include_router(groups.router)           # /api/groups
app.include_router(users.router)            # /api/users
app.include_router(settings_router.router)  # /api/settings
app.include_router(ui_actions.router)       # /ui/file-action-acl
app.include_router(browse.router)           # /api/browse

# ── Статика (собранный Vue) ──────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index():
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"status": "NcAclManager ExApp running", "ui": "not built — run npm run build in vue/"}
else:
    @app.get("/")
    async def index_fallback():
        return {"status": "NcAclManager ExApp running", "ui": "static/ directory missing"}


# ── Запуск через nc_py_api (регистрация в NC) ────────────────────────
# Используется при запуске напрямую: python -m src.main
# В Docker запускается через uvicorn (см. Dockerfile CMD)

def run_with_registration():
    """
    Запуск с автоматической регистрацией manifest в NC.
    Используется nc_py_api.ex_app для:
      - UI элементов (FilesActions, sidebar)
      - Initial state
      - Permissions
    """
    from nc_py_api.ex_app import run_app, set_handlers, AppAPIAuthMiddleware
    from nc_py_api.ex_app.integration_fastapi import fetch_models_task

    app.add_middleware(AppAPIAuthMiddleware)

    set_handlers(
        app,
        enabled_handler=_on_enabled,
        models_to_fetch=None,
    )

    run_app("src.main:app", log_level="info")


async def _on_enabled(enabled: bool, nc=None) -> str:
    """Вызывается AppAPI при включении/выключении плагина."""
    logger.info("ExApp enabled callback: %s", enabled)

    if enabled and nc is not None:
        # Регистрируем UI элементы при включении
        try:
            await _register_ui(nc)
        except Exception as e:
            logger.error("Ошибка регистрации UI: %s", e)
            return str(e)

    return ""


async def _register_ui(nc) -> None:
    """
    Регистрирует FileAction и Files sidebar script через AppAPI manifest API.
    """
    # FilesActions регистрируется через UI API NC 30+ AppAPI
    # https://github.com/cloud-py-api/app_api/blob/main/docs/tech_details/UiInteraction.md
    await nc.ui.files_dropdown_menu.register(
        name="acl_manager",
        display_name="ACL / Права доступа",
        mime="httpd/unix-directory",  # только для папок
        icon="img/lock.svg",
        action_handler="/ui/file-action-acl",
    )
    logger.info("FilesDropdownMenu зарегистрирован")


if __name__ == "__main__":
    run_with_registration()
