from fastapi import APIRouter, Request, Depends, HTTPException
from src.services import db, agent as agent_svc
from src.services.auth import get_nc_user, get_nc_groups, require_acl_admin

router = APIRouter(prefix="/api/users")


@router.get("/search")
async def search_users(q: str, request: Request, _: str = Depends(require_acl_admin)):
    if len(q) < 3:
        return {"users": []}
    s = await db.get_settings()
    return await agent_svc.search_users(s.agent, q, get_nc_user(request), get_nc_groups(request))


@router.get("/{sam}/manager-chain")
async def manager_chain(sam: str, request: Request, _: str = Depends(require_acl_admin)):
    s = await db.get_settings()
    return await agent_svc.get_manager_chain(s.agent, sam, get_nc_user(request), get_nc_groups(request))
