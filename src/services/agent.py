"""
HTTP клиент к Windows NcAclAgent.
Конвертирует PFX → PEM для mTLS через cryptography.
"""

import os
import tempfile
import httpx
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.backends import default_backend

from src.models.settings import AgentSettings


def _build_headers(settings: AgentSettings, user: str = "", groups: str = "", request_id: str = "") -> dict:
    from datetime import datetime, timezone
    import secrets
    rid = request_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4)
    return {
        "Authorization":    f"Bearer {settings.bearer_token}",
        "Content-Type":     "application/json",
        "Accept":           "application/json",
        "X-Request-Id":     rid,
        "X-Nc-User":        user,
        "X-Nc-User-Groups": groups,
    }


def _get_ssl_context(settings: AgentSettings):
    """
    Возвращает SSL контекст для httpx.
    PFX конвертируется во временные PEM файлы через cryptography.
    """
    import ssl

    ctx = ssl.create_default_context()
    if not settings.verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode    = ssl.CERT_NONE

    if not settings.client_cert or not os.path.exists(settings.client_cert):
        return ctx

    # Читаем PFX
    with open(settings.client_cert, "rb") as f:
        pfx_data = f.read()

    password = settings.cert_password.encode() if settings.cert_password else None

    try:
        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            pfx_data, password, backend=default_backend()
        )
    except Exception as e:
        raise ValueError(f"Ошибка чтения PFX сертификата: {e}")

    # Записываем cert и key во временные файлы
    cert_pem = certificate.public_bytes(Encoding.PEM)
    key_pem  = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

    # Используем временные файлы — они удалятся автоматически
    # Но нам нужно держать их открытыми пока создаём контекст
    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cert_file:
        cert_file.write(cert_pem)
        cert_path = cert_file.name

    with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as key_file:
        key_file.write(key_pem)
        key_path = key_file.name

    try:
        ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
    finally:
        os.unlink(cert_path)
        os.unlink(key_path)

    return ctx


def _make_client(settings: AgentSettings) -> httpx.AsyncClient:
    ssl_ctx = _get_ssl_context(settings)
    return httpx.AsyncClient(
        base_url=settings.agent_url.rstrip("/"),
        verify=ssl_ctx,
        timeout=settings.timeout,
    )


async def health_check(settings: AgentSettings) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings)
        resp = await client.get("/api/acl/health", headers=headers)
        resp.raise_for_status()
        return resp.json()


async def get_acl(settings: AgentSettings, path: str, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.get("/api/acl", headers=headers, params={"path": path})
        resp.raise_for_status()
        return resp.json()


async def set_acl(settings: AgentSettings, payload: dict, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.post("/api/acl", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


async def remove_acl(settings: AgentSettings, payload: dict, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.request("DELETE", "/api/acl", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


async def get_folder_groups(settings: AgentSettings, path: str, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.get("/api/groups", headers=headers, params={"path": path})
        resp.raise_for_status()
        return resp.json()


async def create_folder_groups(settings: AgentSettings, payload: dict, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.post("/api/groups", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


async def delete_folder_groups(settings: AgentSettings, path: str, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.request("DELETE", "/api/groups", headers=headers,
                                    json={"folderPath": path, "initiatedByUser": user})
        resp.raise_for_status()
        return resp.json()


async def get_group_members(settings: AgentSettings, group_name: str, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.get(f"/api/groups/{group_name}/members", headers=headers)
        resp.raise_for_status()
        return resp.json()


async def add_group_member(settings: AgentSettings, group_name: str,
                           payload: dict, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.post(f"/api/groups/{group_name}/members", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


async def remove_group_member(settings: AgentSettings, group_name: str,
                              user_sam: str, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.request("DELETE", f"/api/groups/{group_name}/members/{user_sam}",
                                    headers=headers, json={"initiatedByUser": user})
        resp.raise_for_status()
        return resp.json()


async def search_users(settings: AgentSettings, q: str, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.get("/api/users/search", headers=headers, params={"q": q})
        resp.raise_for_status()
        return resp.json()


async def get_manager_chain(settings: AgentSettings, sam: str, user: str, groups: str) -> dict:
    async with _make_client(settings) as client:
        headers = _build_headers(settings, user, groups)
        resp = await client.get(f"/api/users/{sam}/manager-chain", headers=headers)
        resp.raise_for_status()
        return resp.json()
