from fastapi import APIRouter, Request, Depends, HTTPException
from src.models.settings import SetAclRequest, RemoveAclRequest
from src.services import db, agent as agent_svc
from src.services.auth import get_nc_user, get_nc_groups, require_acl_admin

router = APIRouter(prefix="/api/acl")


@router.get("")
async def get_acl(path: str, request: Request, _: str = Depends(require_acl_admin)):
    s      = await db.get_settings()
    user   = get_nc_user(request)
    groups = get_nc_groups(request)
    return await agent_svc.get_acl(s.agent, path, user, groups)


@router.post("")
async def set_acl(body: SetAclRequest, request: Request, _: str = Depends(require_acl_admin)):
    s      = await db.get_settings()
    user   = get_nc_user(request)
    groups = get_nc_groups(request)
    payload = body.model_dump(by_alias=False)
    payload["initiatedByUser"] = user
    return await agent_svc.set_acl(s.agent, payload, user, groups)


@router.delete("")
async def remove_acl(body: RemoveAclRequest, request: Request, _: str = Depends(require_acl_admin)):
    s      = await db.get_settings()
    user   = get_nc_user(request)
    groups = get_nc_groups(request)
    payload = body.model_dump(by_alias=False)
    payload["initiatedByUser"] = user
    return await agent_svc.remove_acl(s.agent, payload, user, groups)


@router.get("/health")
async def health():
    return {"status": "ok"}
