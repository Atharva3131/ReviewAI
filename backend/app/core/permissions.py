"""
Permission system for role-based and organization-based access control
"""

from enum import Enum
from typing import Any, Dict, List, Set

from fastapi import HTTPException, status

from app.models.user import UserRole


class Permission(str, Enum):
    """System permissions enumeration"""

    # Organization management
    ORG_READ = "org:read"
    ORG_UPDATE = "org:update"
    ORG_DELETE = "org:delete"
    ORG_SETTINGS = "org:settings"

    # User management
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ROLES = "user:roles"

    # Review management
    REVIEW_READ = "review:read"
    REVIEW_CREATE = "review:create"
    REVIEW_UPDATE = "review:update"
    REVIEW_DELETE = "review:delete"
    REVIEW_RESPOND = "review:respond"
    REVIEW_ESCALATE = "review:escalate"

    # Customer management
    CUSTOMER_READ = "customer:read"
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_UPDATE = "customer:update"
    CUSTOMER_DELETE = "customer:delete"
    CUSTOMER_EXPORT = "customer:export"

    # Support ticket management
    TICKET_READ = "ticket:read"
    TICKET_CREATE = "ticket:create"
    TICKET_UPDATE = "ticket:update"
    TICKET_DELETE = "ticket:delete"
    TICKET_ASSIGN = "ticket:assign"
    TICKET_RESOLVE = "ticket:resolve"

    # Recovery action management
    RECOVERY_READ = "recovery:read"
    RECOVERY_CREATE = "recovery:create"
    RECOVERY_UPDATE = "recovery:update"
    RECOVERY_DELETE = "recovery:delete"
    RECOVERY_EXECUTE = "recovery:execute"
    RECOVERY_APPROVE = "recovery:approve"

    # Agent decision management
    AGENT_READ = "agent:read"
    AGENT_APPROVE = "agent:approve"
    AGENT_REJECT = "agent:reject"
    AGENT_CONFIGURE = "agent:configure"

    # Analytics and reporting
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # System administration
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_SETTINGS = "system:settings"


class PermissionManager:
    """Manages role-based permissions"""

    # Role-based permission mapping
    ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
        UserRole.USER: {
            Permission.ORG_READ,
            Permission.USER_READ,
            Permission.REVIEW_READ,
            Permission.CUSTOMER_READ,
            Permission.TICKET_READ,
            Permission.TICKET_CREATE,
            Permission.TICKET_UPDATE,
            Permission.RECOVERY_READ,
            Permission.AGENT_READ,
            Permission.ANALYTICS_READ,
        },
        UserRole.MANAGER: {
            # All user permissions plus:
            Permission.ORG_READ,
            Permission.ORG_UPDATE,
            Permission.USER_READ,
            Permission.USER_CREATE,
            Permission.USER_UPDATE,
            Permission.REVIEW_READ,
            Permission.REVIEW_CREATE,
            Permission.REVIEW_UPDATE,
            Permission.REVIEW_RESPOND,
            Permission.REVIEW_ESCALATE,
            Permission.CUSTOMER_READ,
            Permission.CUSTOMER_CREATE,
            Permission.CUSTOMER_UPDATE,
            Permission.CUSTOMER_EXPORT,
            Permission.TICKET_READ,
            Permission.TICKET_CREATE,
            Permission.TICKET_UPDATE,
            Permission.TICKET_ASSIGN,
            Permission.TICKET_RESOLVE,
            Permission.RECOVERY_READ,
            Permission.RECOVERY_CREATE,
            Permission.RECOVERY_UPDATE,
            Permission.RECOVERY_EXECUTE,
            Permission.RECOVERY_APPROVE,
            Permission.AGENT_READ,
            Permission.AGENT_APPROVE,
            Permission.AGENT_REJECT,
            Permission.ANALYTICS_READ,
            Permission.ANALYTICS_EXPORT,
        },
        UserRole.ADMIN: {
            # All permissions
            *[perm for perm in Permission]
        },
    }

    @classmethod
    def get_role_permissions(cls, role: UserRole) -> Set[Permission]:
        """Get permissions for a specific role"""
        return cls.ROLE_PERMISSIONS.get(role, set())

    @classmethod
    def has_permission(cls, user_role: UserRole, permission: Permission) -> bool:
        """Check if role has specific permission"""
        role_permissions = cls.get_role_permissions(user_role)
        return permission in role_permissions

    @classmethod
    def has_any_permission(
        cls, user_role: UserRole, permissions: List[Permission]
    ) -> bool:
        """Check if role has any of the specified permissions"""
        role_permissions = cls.get_role_permissions(user_role)
        return any(perm in role_permissions for perm in permissions)

    @classmethod
    def has_all_permissions(
        cls, user_role: UserRole, permissions: List[Permission]
    ) -> bool:
        """Check if role has all specified permissions"""
        role_permissions = cls.get_role_permissions(user_role)
        return all(perm in role_permissions for perm in permissions)

    @classmethod
    def require_permission(cls, user_role: UserRole, permission: Permission):
        """Raise exception if role doesn't have permission"""
        if not cls.has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}",
            )

    @classmethod
    def require_any_permission(cls, user_role: UserRole, permissions: List[Permission]):
        """Raise exception if role doesn't have any of the permissions"""
        if not cls.has_any_permission(user_role, permissions):
            perm_names = [perm.value for perm in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {', '.join(perm_names)}",
            )

    @classmethod
    def require_all_permissions(
        cls, user_role: UserRole, permissions: List[Permission]
    ):
        """Raise exception if role doesn't have all permissions"""
        if not cls.has_all_permissions(user_role, permissions):
            perm_names = [perm.value for perm in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all of: {', '.join(perm_names)}",
            )


class OrganizationAccessControl:
    """Handles organization-based access control"""

    @staticmethod
    def require_organization_access(user_org_id: str, resource_org_id: str):
        """Ensure user can only access resources from their organization"""
        if user_org_id != resource_org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Resource belongs to different organization",
            )

    @staticmethod
    def filter_by_organization(query, model_class, user_org_id: str):
        """Filter query results by organization"""
        return query.where(model_class.organization_id == user_org_id)

    @staticmethod
    def validate_organization_resource(resource: Any, user_org_id: str):
        """Validate that resource belongs to user's organization"""
        if hasattr(resource, "organization_id"):
            if str(resource.organization_id) != user_org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Resource belongs to different organization",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Resource does not have organization association",
            )


class AccessControlContext:
    """Context object for access control information"""

    def __init__(self, user_id: str, organization_id: str, role: UserRole, email: str):
        self.user_id = user_id
        self.organization_id = organization_id
        self.role = role
        self.email = email
        self.permissions = PermissionManager.get_role_permissions(role)

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions

    def require_permission(self, permission: Permission):
        """Require specific permission or raise exception"""
        PermissionManager.require_permission(self.role, permission)

    def require_organization_access(self, resource_org_id: str):
        """Require access to organization resource"""
        OrganizationAccessControl.require_organization_access(
            self.organization_id, resource_org_id
        )

    def validate_resource_access(self, resource: Any):
        """Validate access to organization resource"""
        OrganizationAccessControl.validate_organization_resource(
            resource, self.organization_id
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "role": self.role.value,
            "email": self.email,
            "permissions": [perm.value for perm in self.permissions],
        }
