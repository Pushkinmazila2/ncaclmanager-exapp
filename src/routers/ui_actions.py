"""
UI Action handlers — вызываются AppAPI когда пользователь
кликает на зарегистрированный пункт меню/действие в NC Files.

NC передаёт сюда info о файле/папке на которой кликнули.
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ui")


@router.post("/file-action-acl")
async def file_action_acl(request: Request):
    """
    Вызывается когда пользователь кликает "ACL / Права доступа"
    в выпадающем меню файла/папки.

    NC передаёт actionFile с информацией о узле:
    {
      "actionName": "acl_manager",
      "actionFile": {
        "fileId": 117,
        "name": "...",
        "directory": "/test/linux",
        "etag": "...",
        "mime": "httpd/unix-directory",
        "favorite": false,
        "permissions": 31,
        "mtime": ...,
        "size": ...,
        "userId": "admin"
      }
    }

    Возвращаем редирект на страницу ExApp с открытой ACL панелью
    либо просто подтверждение — UI откроется через postMessage/iframe.
    """
    try:
        body = await request.json()
        logger.info("file-action-acl вызван: %s", body)

        action_file = body.get("actionFile", {})
        directory   = action_file.get("directory", "/")
        name        = action_file.get("name", "")
        full_path   = (directory.rstrip("/") + "/" + name) if name else directory

        # AppAPI ожидает ответ с типом действия:
        # "message" — просто уведомление
        # "redirect_url" — открыть URL (в новой вкладке или iframe)
        return JSONResponse({
            "type":    "message",
            "message": f"Открываю ACL для: {full_path}",
            # Frontend слушает это через polling или WebSocket для
            # синхронизации какая папка должна открыться
        })
    except Exception as e:
        logger.error("file-action-acl error: %s", e)
        return JSONResponse({"type": "error", "message": str(e)}, status_code=500)
