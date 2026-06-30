from fastapi import APIRouter, Request, Depends
from src.models.settings import CreateGroupsRequest, GroupMemberRequest
from src.services import db, agent as agent_svc
from src.services.auth import get_nc_user, get_nc_groups, require_acl_admin

router = APIRouter(prefix="/api/groups")


@router.get("")
async def get_folder_groups(path: str, request: Request, _: str = Depends(require_acl_admin)):
    s = await db.get_settings()
    return await agent_svc.get_folder_groups(s.agent, path, get_nc_user(request), get_nc_groups(request))


@router.post("")
async def create_folder_groups(body: CreateGroupsRequest, request: Request,
                               _: str = Depends(require_acl_admin)):
    s    = await db.get_settings()
    user = get_nc_user(request)
    payload = {
        "folderPath":       body.folder_path,
        "initiatedByUser":  user,
        "suffixes":         body.suffixes,
        "comment":          body.comment,
    }
    return await agent_svc.create_folder_groups(s.agent, payload, user, get_nc_groups(request))


@router.delete("")
async def delete_folder_groups(path: str, request: Request, _: str = Depends(require_acl_admin)):
    s    = await db.get_settings()
    user = get_nc_user(request)
    return await agent_svc.delete_folder_groups(s.agent, path, user, get_nc_groups(request))


@router.get("/{group_name}/members")
async def get_members(group_name: str, request: Request, _: str = Depends(require_acl_admin)):
    s = await db.get_settings()
    return await agent_svc.get_group_members(s.agent, group_name,
                                             get_nc_user(request), get_nc_groups(request))


@router.post("/{group_name}/members")
async def add_member(group_name: str, body: GroupMemberRequest,
                     request: Request, _: str = Depends(require_acl_admin)):
    s    = await db.get_settings()
    user = get_nc_user(request)
    payload = {
        "userSamName":     body.user_sam_name,
        "initiatedByUser": user,
        "comment":         body.comment,
    }
    return await agent_svc.add_group_member(s.agent, group_name, payload,
                                            user, get_nc_groups(request))


@router.delete("/{group_name}/members/{user_sam}")
async def remove_member(group_name: str, user_sam: str,
                        request: Request, _: str = Depends(require_acl_admin)):
    s    = await db.get_settings()
    user = get_nc_user(request)
    return await agent_svc.remove_group_member(s.agent, group_name, user_sam,
                                               user, get_nc_groups(request))
