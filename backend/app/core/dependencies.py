"""
FastAPI dependencies for authentication and authorization
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security import SecurityService
from app.core.permissions import Permission, PermissionManager, AccessControlContext
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.services.auth_service import AuthService

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Get current authenticated user from JWT token
    """
    try:
        # Extract user ID from token
        user_id = SecurityService.get_user_id_from_token(credentials.credentials)
        
        # Get user from database
        user = await AuthService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_organization(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
) -> Organization:
    """
    Get current user's organization
    """
    organization = await db.get(Organization, user.organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Organization not found"
        )
    return organization


async def get_access_control_context(
    user: User = Depends(get_current_user),
    organization: Organization = Depends(get_current_organization)
) -> AccessControlContext:
    """
    Get access control context for current user
    """
    return AccessControlContext(
        user_id=str(user.id),
        organization_id=str(organization.id),
        role=user.role,
        email=user.email
    )


def require_permission(permission: Permission):
    """
    Dependency factory for requiring specific permission
    """
    async def permission_dependency(
        context: AccessControlContext = Depends(get_access_control_context)
    ) -> AccessControlContext:
        context.require_permission(permission)
        return context
    
    return permission_dependency


def require_any_permission(*permissions: Permission):
    """
    Dependency factory for requiring any of the specified permissions
    """
    async def permission_dependency(
        context: AccessControlContext = Depends(get_access_control_context)
    ) -> AccessControlContext:
        PermissionManager.require_any_permission(context.role, list(permissions))
        return context
    
    return permission_dependency


def require_role(role: UserRole):
    """
    Dependency factory for requiring specific role
    """
    async def role_dependency(
        user: User = Depends(get_current_user)
    ) -> User:
        if user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {role.value}"
            )
        return user
    
    return role_dependency


def require_admin():
    """
    Dependency for requiring admin role
    """
    return require_role(UserRole.ADMIN)


def require_manager_or_admin():
    """
    Dependency for requiring manager or admin role
    """
    async def role_dependency(
        user: User = Depends(get_current_user)
    ) -> User:
        if user.role not in [UserRole.MANAGER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Required role: manager or admin"
            )
        return user
    
    return role_dependency


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_async_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None
    Useful for endpoints that work for both authenticated and anonymous users
    """
    if not credentials:
        return None
    
    try:
        user_id = SecurityService.get_user_id_from_token(credentials.credentials)
        user = await AuthService.get_user_by_id(db, user_id)
        return user if user and user.is_active else None
    except Exception:
        return None


class OrganizationFilter:
    """
    Utility class for filtering resources by organization
    """
    
    def __init__(self, context: AccessControlContext):
        self.context = context
    
    def filter_query(self, query, model_class):
        """Filter query by organization"""
        return query.where(model_class.organization_id == self.context.organization_id)
    
    def validate_resource(self, resource):
        """Validate resource belongs to user's organization"""
        self.context.validate_resource_access(resource)


def get_organization_filter(
    context: AccessControlContext = Depends(get_access_control_context)
) -> OrganizationFilter:
    """
    Get organization filter for current user
    """
    return OrganizationFilter(context)


# Common permission dependencies
require_user_read = require_permission(Permission.USER_READ)
require_user_create = require_permission(Permission.USER_CREATE)
require_user_update = require_permission(Permission.USER_UPDATE)
require_user_delete = require_permission(Permission.USER_DELETE)

require_review_read = require_permission(Permission.REVIEW_READ)
require_review_create = require_permission(Permission.REVIEW_CREATE)
require_review_update = require_permission(Permission.REVIEW_UPDATE)
require_review_respond = require_permission(Permission.REVIEW_RESPOND)

require_customer_read = require_permission(Permission.CUSTOMER_READ)
require_customer_create = require_permission(Permission.CUSTOMER_CREATE)
require_customer_update = require_permission(Permission.CUSTOMER_UPDATE)

require_ticket_read = require_permission(Permission.TICKET_READ)
require_ticket_create = require_permission(Permission.TICKET_CREATE)
require_ticket_update = require_permission(Permission.TICKET_UPDATE)

require_recovery_read = require_permission(Permission.RECOVERY_READ)
require_recovery_create = require_permission(Permission.RECOVERY_CREATE)
require_recovery_execute = require_permission(Permission.RECOVERY_EXECUTE)

require_agent_read = require_permission(Permission.AGENT_READ)
require_agent_approve = require_permission(Permission.AGENT_APPROVE)

require_analytics_read = require_permission(Permission.ANALYTICS_READ)
require_analytics_export = require_permission(Permission.ANALYTICS_EXPORT)

require_org_settings = require_permission(Permission.ORG_SETTINGS)


# Alias for backward compatibility
require_organization_access = get_access_control_context


# Import get_db from database module
from app.core.database import get_db
