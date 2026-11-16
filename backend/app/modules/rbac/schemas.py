"""
Pydantic Schemas for RBAC
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    id: int
    code: str
    description: Optional[str] = None
    category: str

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    is_system: bool
    permissions: List[PermissionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssignRoleRequest(BaseModel):
    role_id: int = Field(..., description="ID of the role to assign to the user")


class UserRolesResponse(BaseModel):
    user_id: int
    email: str
    user_type: str
    roles: List[RoleResponse] = Field(default_factory=list)
