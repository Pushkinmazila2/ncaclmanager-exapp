"""
Обязательные endpoints для AppAPI ExApp.

NC проверяет жизнеспособность приложения через GET /heartbeat
и уведомляет о включении/выключении через PUT /enabled.
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Heartbeat ─────────────────────────────────────────────────────────
# NC AppAPI периодически пингует этот endpoint.
# Если не отвечает — помечает ExApp как недоступный.

@router.get("/heartbeat")
async def heartbeat():
    return {"status": "ok"}


# Некоторые версии AppAPI используют /v1.30/_ping или аналог
@router.get("/_ping")
async def ping():
    return {"status": "ok"}


@router.get("/v1.30/_ping")
async def ping_v130():
    return {"status": "ok"}


# ── Init ──────────────────────────────────────────────────────────────
# NC вызывает POST /init когда ExApp первый раз устанавливается
# или когда NC хочет передать начальные данные.
# nc-py-api передаёт сюда данные о NC инстансе.

@router.post("/init")
async def init_handler(request: Request):
    try:
        body = await request.json()
        logger.info("ExApp init: %s", body)
    except Exception:
        pass
    return JSONResponse({"status": "ok"})


# ── Enabled ───────────────────────────────────────────────────────────
# NC вызывает PUT /enabled когда администратор включает или выключает плагин.
# enabled=True  → запускаем фоновые задачи если есть
# enabled=False → останавливаем

@router.put("/enabled")
async def enabled_handler(request: Request):
    try:
        body  = await request.json()
        state = body.get("enabled", True)
        logger.info("ExApp enabled=%s", state)
    except Exception:
        pass
    return JSONResponse({"enabled": True})
