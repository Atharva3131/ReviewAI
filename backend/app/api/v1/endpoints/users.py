"""
User management endpoints
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.dependencies import (
    get_access_control_context,
    require_user_create,
    require_user_delete,
    require_user_read,
    require_user_update,
)
from app.core.permissions import AccessControlContext
from app.models.user import UserRole
from app.schemas.auth import UserResponse
from app.services.user_service import UserService

router = APIRouter()


class UserCreate(BaseModel):
    """User creation schema"""

    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    """User update schema"""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserRoleChange(BaseModel):
    """User role change schema"""

    role: UserRole


class UserInvitation(BaseModel):
    """User invitation schema"""

    email: EmailStr
    role: UserRole = UserRole.USER


class InvitationAcceptance(BaseModel):
    """Invitation acceptance schema"""

    invitation_token: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    active_only: bool = Query(True),
    context: AccessControlContext = Depends(require_user_read),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get users in organization

    Retrieve list of users with optional filtering by role, search term, and active status.
    """
    users = await UserService.get_users_by_organization(
        db=db,
        organization_id=context.organization_id,
        skip=skip,
        limit=limit,
        search=search,
        role_filter=role,
        active_only=active_only,
    )

    return [UserResponse.from_orm(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    context: AccessControlContext = Depends(require_user_read),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get user by ID

    Retrieve detailed information about a specific user.
    """
    user = await UserService.get_user_by_id(
        db=db, user_id=user_id, organization_id=context.organization_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.from_orm(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    context: AccessControlContext = Depends(require_user_create),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create new user

    Create a new user account in the organization.
    """
    user = await UserService.create_user(
        db=db,
        organization_id=context.organization_id,
        email=user_data.email,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        created_by_user_id=context.user_id,
    )

    return UserResponse.from_orm(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    context: AccessControlContext = Depends(require_user_update),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update user information

    Update user profile information and account status.
    """
    updates = user_data.dict(exclude_unset=True)

    user = await UserService.update_user(
        db=db,
        user_id=user_id,
        organization_id=context.organization_id,
        updates=updates,
        updated_by_user_id=context.user_id,
    )

    return UserResponse.from_orm(user)


@router.patch("/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: str,
    role_data: UserRoleChange,
    context: AccessControlContext = Depends(require_user_update),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Change user role

    Change the role of a user within the organization.
    """
    user = await UserService.change_user_role(
        db=db,
        user_id=user_id,
        organization_id=context.organization_id,
        new_role=role_data.role,
        changed_by_user_id=context.user_id,
        changed_by_role=context.role,
    )

    return UserResponse.from_orm(user)


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: str,
    context: AccessControlContext = Depends(require_user_delete),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Deactivate user account

    Deactivate a user account, preventing login while preserving data.
    """
    user = await UserService.deactivate_user(
        db=db,
        user_id=user_id,
        organization_id=context.organization_id,
        deactivated_by_user_id=context.user_id,
        deactivated_by_role=context.role,
    )

    return UserResponse.from_orm(user)


@router.patch("/{user_id}/reactivate", response_model=UserResponse)
async def reactivate_user(
    user_id: str,
    context: AccessControlContext = Depends(require_user_update),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Reactivate user account

    Reactivate a previously deactivated user account.
    """
    user = await UserService.reactivate_user(
        db=db,
        user_id=user_id,
        organization_id=context.organization_id,
        reactivated_by_role=context.role,
    )

    return UserResponse.from_orm(user)


@router.get("/{user_id}/permissions", response_model=List[str])
async def get_user_permissions(
    user_id: str,
    context: AccessControlContext = Depends(require_user_read),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get user permissions

    Retrieve list of permissions for a specific user based on their role.
    """
    permissions = await UserService.get_user_permissions(
        db=db, user_id=user_id, organization_id=context.organization_id
    )

    return permissions


@router.post("/invite")
async def invite_user(
    invitation_data: UserInvitation,
    context: AccessControlContext = Depends(require_user_create),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Invite user to organization

    Send an invitation to join the organization to the specified email address.
    """
    result = await UserService.invite_user(
        db=db,
        organization_id=context.organization_id,
        email=invitation_data.email,
        role=invitation_data.role,
        invited_by_user_id=context.user_id,
        invited_by_role=context.role,
    )

    return result


@router.post("/accept-invitation", response_model=UserResponse)
async def accept_invitation(
    acceptance_data: InvitationAcceptance, db: AsyncSession = Depends(get_async_db)
):
    """
    Accept user invitation

    Accept an invitation and create a new user account.
    """
    user = await UserService.accept_invitation(
        db=db,
        invitation_token=acceptance_data.invitation_token,
        password=acceptance_data.password,
        first_name=acceptance_data.first_name,
        last_name=acceptance_data.last_name,
    )

    return UserResponse.from_orm(user)


@router.get("/organization/stats")
async def get_organization_user_stats(
    context: AccessControlContext = Depends(require_user_read),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get organization user statistics

    Retrieve statistics about users in the organization.
    """
    stats = await UserService.get_organization_stats(
        db=db, organization_id=context.organization_id
    )

    return stats


class OnboardingData(BaseModel):
    """Onboarding data schema"""

    business_type: Optional[str] = None
    review_platforms: Optional[List[str]] = None
    email_provider: Optional[str] = None
    goals: Optional[List[str]] = None
    team_size: Optional[str] = None
    onboarding_completed: bool = True


@router.post("/complete-onboarding", response_model=UserResponse)
async def complete_onboarding(
    onboarding_data: OnboardingData,
    context: AccessControlContext = Depends(get_access_control_context),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Complete user onboarding

    Save onboarding preferences and mark onboarding as completed.
    """
    updates = {
        "onboarding_completed": onboarding_data.onboarding_completed,
        "onboarding_data": onboarding_data.dict(exclude={"onboarding_completed"}),
    }

    user = await UserService.update_user(
        db=db,
        user_id=context.user_id,
        organization_id=context.organization_id,
        updates=updates,
        updated_by_user_id=context.user_id,
    )

    return UserResponse.from_orm(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    context: AccessControlContext = Depends(get_access_control_context),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get current user profile

    Retrieve the authenticated user's profile information.
    """
    user = await UserService.get_user_by_id(
        db=db, user_id=context.user_id, organization_id=context.organization_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.from_orm(user)
