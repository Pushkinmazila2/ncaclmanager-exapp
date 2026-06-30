from pydantic import BaseModel, Field
from typing import Optional


class AgentSettings(BaseModel):
    agent_url:    str = ""
    bearer_token: str = ""
    client_cert:  str = ""
    cert_password: str = ""
    timeout:      int = 10
    verify_ssl:   bool = True


class PathMapping(BaseModel):
    nc_path:     str = Field(..., description="NC путь: /mountpoint")
    unc_path:    str = Field(..., description="UNC путь: \\\\SERVER\\Share")
    description: str = ""


class AdminGroupsSettings(BaseModel):
    admin_groups:    list[str] = []
    nc_admin_users:  list[str] = []
    owner_mode:      bool = False


class FullSettings(BaseModel):
    agent:     AgentSettings      = AgentSettings()
    groups:    AdminGroupsSettings = AdminGroupsSettings()
    mappings:  list[PathMapping]  = []
    agent_mode: str               = ""  # кэш: Test | Prod


class AclEntry(BaseModel):
    identity_reference: str
    permission:         str
    action:             str
    is_inherited:       bool = False


class SetAclRequest(BaseModel):
    path:              str
    group_identity:    str
    permission:        str
    action:            str = "Allow"
    initiated_by_user: str
    comment:           Optional[str] = None


class RemoveAclRequest(BaseModel):
    path:              str
    group_identity:    str
    initiated_by_user: str
    comment:           Optional[str] = None


class CreateGroupsRequest(BaseModel):
    folder_path:       str
    initiated_by_user: str
    suffixes:          list[str] = ["RO", "RX", "RW"]
    comment:           Optional[str] = None


class GroupMemberRequest(BaseModel):
    user_sam_name:     str
    comment:           Optional[str] = None
