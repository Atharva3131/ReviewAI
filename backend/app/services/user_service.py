"""
User management service for role management and user operations
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from fastapi import HTTPException, status
from datetime import datetime, timezone
import uuid

from app.models.user import User, UserRole
from app.models.organization import Organization
from app.core.security import SecurityService
from app.core.permissions import Permission, PermissionManager, AccessControlContext
from app.schemas.auth import UserResponse


class UserService:
    """Service for user management operations"""
    
    @staticmethod
    async def get_users_by_organization(
        db: AsyncSession,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        role_filter: Optional[UserRole] = None,
        active_only: bool = True
    ) -> List[User]:
        """Get users in organization with filtering"""
        
        query = select(User).where(User.organization_id == organization_id)
        
        # Apply filters
        if active_only:
            query = query.where(User.is_active == True)
        
        if role_filter:
            query = query.where(User.role == role_filter)
        
        if search:
            search_term = f"%{search.lower()}%"
            query = query.where(
                or_(
                    func.lower(User.email).like(search_term),
                    func.lower(User.first_name).like(search_term),
                    func.lower(User.last_name).like(search_term)
                )
            )
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: str,
        organization_id: str
    ) -> Optional[User]:
        """Get user by ID within organization"""
        try:
            user_uuid = uuid.UUID(user_id)
            result = await db.execute(
                select(User).where(
                    and_(
                        User.id == user_uuid,
                        User.organization_id == organization_id
                    )
                )
            )
            return result.scalar_one_or_none()
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    async def create_user(
        db: AsyncSession,
        organization_id: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
        created_by_user_id: str = None
    ) -> User:
        """Create new user in organization"""
        
        # Check if user already exists
        existing_user = await db.execute(
            select(User).where(User.email == email.lower())
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Validate password
        password_validation = SecurityService.validate_password_strength(password)
        if not password_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet security requirements"
            )
        
        # Create user
        user = User(
            organization_id=organization_id,
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
            is_verified=False
        )
        user.set_password(password)
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: str,
        organization_id: str,
        updates: Dict[str, Any],
        updated_by_user_id: str
    ) -> User:
        """Update user information"""
        
        user = await UserService.get_user_by_id(db, user_id, organization_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update allowed fields
        allowed_fields = {
            "first_name", "last_name", "is_active", "is_verified"
        }
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def change_user_role(
        db: AsyncSession,
        user_id: str,
        organization_id: str,
        new_role: UserRole,
        changed_by_user_id: str,
        changed_by_role: UserRole
    ) -> User:
        """Change user role with permission validation"""
        
        # Get user to update
        user = await UserService.get_user_by_id(db, user_id, organization_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate permissions for role change
        if not UserService._can_change_role(changed_by_role, user.role, new_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to change user role"
            )
        
        # Prevent self-demotion from admin
        if (user_id == changed_by_user_id and 
            user.role == UserRole.ADMIN and 
            new_role != UserRole.ADMIN):
            
            # Check if there are other admins
            admin_count = await db.execute(
                select(func.count(User.id)).where(
                    and_(
                        User.organization_id == organization_id,
                        User.role == UserRole.ADMIN,
                        User.is_active == True,
                        User.id != user.id
                    )
                )
            )
            
            if admin_count.scalar() == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove admin role - organization must have at least one admin"
                )
        
        # Update role
        user.role = new_role
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def deactivate_user(
        db: AsyncSession,
        user_id: str,
        organization_id: str,
        deactivated_by_user_id: str,
        deactivated_by_role: UserRole
    ) -> User:
        """Deactivate user account"""
        
        user = await UserService.get_user_by_id(db, user_id, organization_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate permissions
        if not PermissionManager.has_permission(deactivated_by_role, Permission.USER_DELETE):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to deactivate user"
            )
        
        # Prevent self-deactivation
        if user_id == deactivated_by_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        # Prevent deactivating the last admin
        if user.role == UserRole.ADMIN:
            admin_count = await db.execute(
                select(func.count(User.id)).where(
                    and_(
                        User.organization_id == organization_id,
                        User.role == UserRole.ADMIN,
                        User.is_active == True,
                        User.id != user.id
                    )
                )
            )
            
            if admin_count.scalar() == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the last admin user"
                )
        
        user.is_active = False
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def reactivate_user(
        db: AsyncSession,
        user_id: str,
        organization_id: str,
        reactivated_by_role: UserRole
    ) -> User:
        """Reactivate user account"""
        
        user = await UserService.get_user_by_id(db, user_id, organization_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate permissions
        if not PermissionManager.has_permission(reactivated_by_role, Permission.USER_UPDATE):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to reactivate user"
            )
        
        user.is_active = True
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def get_user_permissions(
        db: AsyncSession,
        user_id: str,
        organization_id: str
    ) -> List[str]:
        """Get user permissions based on role"""
        
        user = await UserService.get_user_by_id(db, user_id, organization_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        permissions = PermissionManager.get_role_permissions(user.role)
        return [perm.value for perm in permissions]
    
    @staticmethod
    async def get_organization_stats(
        db: AsyncSession,
        organization_id: str
    ) -> Dict[str, Any]:
        """Get organization user statistics"""
        
        # Total users
        total_users = await db.execute(
            select(func.count(User.id)).where(User.organization_id == organization_id)
        )
        
        # Active users
        active_users = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.organization_id == organization_id,
                    User.is_active == True
                )
            )
        )
        
        # Users by role
        role_counts = await db.execute(
            select(User.role, func.count(User.id)).where(
                and_(
                    User.organization_id == organization_id,
                    User.is_active == True
                )
            ).group_by(User.role)
        )
        
        role_distribution = {role.value: 0 for role in UserRole}
        for role, count in role_counts:
            role_distribution[role.value] = count
        
        return {
            "total_users": total_users.scalar(),
            "active_users": active_users.scalar(),
            "inactive_users": total_users.scalar() - active_users.scalar(),
            "role_distribution": role_distribution
        }
    
    @staticmethod
    def _can_change_role(
        changer_role: UserRole, 
        current_role: UserRole, 
        new_role: UserRole
    ) -> bool:
        """Validate if user can change another user's role"""
        
        # Only admins can change roles
        if changer_role != UserRole.ADMIN:
            return False
        
        # Admins can change any role
        return True
    
    @staticmethod
    async def invite_user(
        db: AsyncSession,
        organization_id: str,
        email: str,
        role: UserRole,
        invited_by_user_id: str,
        invited_by_role: UserRole
    ) -> Dict[str, str]:
        """Invite user to organization"""
        
        # Validate permissions
        if not PermissionManager.has_permission(invited_by_role, Permission.USER_CREATE):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to invite users"
            )
        
        # Check if user already exists
        existing_user = await db.execute(
            select(User).where(User.email == email.lower())
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Generate invitation token
        invitation_token = SecurityService.generate_verification_token()
        
        # Store invitation in Redis
        from app.core.redis import redis_client
        invitation_data = {
            "organization_id": organization_id,
            "email": email.lower(),
            "role": role.value,
            "invited_by": invited_by_user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await redis_client.set_json(
            f"invitation:{invitation_token}",
            invitation_data,
            expire=7 * 24 * 60 * 60  # 7 days
        )
        
        # In a real implementation, send invitation email here
        # await EmailService.send_invitation_email(email, invitation_token)
        
        return {
            "message": "Invitation sent successfully",
            "invitation_token": invitation_token  # For testing purposes
        }
    
    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        invitation_token: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """Accept user invitation and create account"""
        
        # Get invitation data
        from app.core.redis import redis_client
        invitation_data = await redis_client.get_json(f"invitation:{invitation_token}")
        
        if not invitation_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invitation token"
            )
        
        # Validate password
        password_validation = SecurityService.validate_password_strength(password)
        if not password_validation["is_valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet security requirements"
            )
        
        # Create user
        user = await UserService.create_user(
            db=db,
            organization_id=invitation_data["organization_id"],
            email=invitation_data["email"],
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=UserRole(invitation_data["role"]),
            created_by_user_id=invitation_data["invited_by"]
        )
        
        # Mark as verified since they accepted invitation
        user.is_verified = True
        await db.commit()
        
        # Delete invitation token
        await redis_client.delete(f"invitation:{invitation_token}")
        
        return user
