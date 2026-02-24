"""
Authentication service for user management and authentication
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import uuid

from app.models.user import User, UserRole
from app.models.organization import Organization
from app.core.security import SecurityService, TokenData
from app.schemas.auth import UserRegistration, UserLogin, TokenResponse, UserResponse, OrganizationResponse
from app.core.redis import redis_client
from app.core.config import settings


class AuthService:
    """Service for handling authentication operations"""
    
    @staticmethod
    async def register_user(
        db: AsyncSession, 
        registration_data: UserRegistration
    ) -> Tuple[User, Organization]:
        """Register new user and organization"""
        
        # Check if user already exists
        existing_user = await AuthService.get_user_by_email(db, registration_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create organization first
        organization = Organization(
            name=registration_data.organization_name,
            domain=registration_data.organization_domain,
            settings={}
        )
        db.add(organization)
        await db.flush()  # Get the organization ID
        
        # Create user
        user = User(
            organization_id=organization.id,
            email=registration_data.email,
            first_name=registration_data.first_name,
            last_name=registration_data.last_name,
            role=UserRole.ADMIN,  # First user is admin
            is_active=True,
            is_verified=False  # Require email verification
        )
        user.set_password(registration_data.password)
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        await db.refresh(organization)
        
        return user, organization
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession, 
        login_data: UserLogin
    ) -> Tuple[User, Organization]:
        """Authenticate user credentials"""
        
        user = await AuthService.get_user_by_email(db, login_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is locked
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to failed login attempts"
            )
        
        # Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Verify password
        if not user.verify_password(login_data.password):
            # Increment failed login attempts
            user.increment_failed_login()
            await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Reset failed login attempts on successful login
        user.reset_failed_login()
        await db.commit()
        
        # Get organization
        organization = await db.get(Organization, user.organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Organization not found"
            )
        
        return user, organization
    
    @staticmethod
    async def create_tokens(user: User, organization: Organization) -> TokenResponse:
        """Create access and refresh tokens for user"""
        
        # Create token data
        token_data = TokenData(
            user_id=str(user.id),
            organization_id=str(organization.id),
            email=user.email,
            role=user.role.value
        )
        
        # Create tokens
        access_token = SecurityService.create_access_token(token_data.to_dict())
        refresh_token = SecurityService.create_refresh_token(str(user.id))
        
        # Store refresh token in Redis
        try:
            await redis_client.set(
                f"refresh_token:{user.id}",
                refresh_token,
                expire=30 * 24 * 60 * 60  # 30 days
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to store refresh token in Redis: {e}")
            # Continue anyway - token will still work, just won't be tracked in Redis
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
            organization=OrganizationResponse.model_validate(organization)
        )
    
    @staticmethod
    async def refresh_access_token(
        db: AsyncSession, 
        refresh_token: str
    ) -> TokenResponse:
        """Refresh access token using refresh token"""
        
        try:
            # Verify refresh token
            payload = SecurityService.verify_token(refresh_token)
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if not user_id or token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Check if refresh token exists in Redis
            stored_token = await redis_client.get(f"refresh_token:{user_id}")
            if not stored_token or stored_token != refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token not found or expired"
                )
            
            # Get user and organization
            user = await db.get(User, user_id)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            organization = await db.get(Organization, user.organization_id)
            if not organization:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Organization not found"
                )
            
            # Create new tokens
            return await AuthService.create_tokens(user, organization)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            ) from e
    
    @staticmethod
    async def logout_user(user_id: str) -> bool:
        """Logout user by invalidating refresh token"""
        try:
            await redis_client.delete(f"refresh_token:{user_id}")
            return True
        except Exception:
            return False
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address"""
        result = await db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            user_uuid = uuid.UUID(user_id)
            return await db.get(User, user_uuid)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    async def verify_user_email(db: AsyncSession, user_id: str) -> bool:
        """Mark user email as verified"""
        user = await AuthService.get_user_by_id(db, user_id)
        if user:
            user.is_verified = True
            await db.commit()
            return True
        return False
    
    @staticmethod
    async def change_password(
        db: AsyncSession, 
        user_id: str, 
        current_password: str, 
        new_password: str
    ) -> bool:
        """Change user password"""
        user = await AuthService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not user.verify_password(current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Set new password
        user.set_password(new_password)
        await db.commit()
        
        # Invalidate all refresh tokens for security
        await redis_client.delete(f"refresh_token:{user_id}")
        
        return True
    
    @staticmethod
    async def reset_password(
        db: AsyncSession, 
        email: str
    ) -> str:
        """Initiate password reset process"""
        user = await AuthService.get_user_by_email(db, email)
        if not user:
            # Don't reveal if email exists for security
            return "If the email exists, a reset link has been sent"
        
        # Generate reset token
        reset_token = SecurityService.generate_password_reset_token()
        
        # Store reset token in Redis with 1 hour expiration
        await redis_client.set(
            f"password_reset:{reset_token}",
            str(user.id),
            expire=60 * 60  # 1 hour
        )
        
        # In a real implementation, send email here
        # await EmailService.send_password_reset_email(user.email, reset_token)
        
        return "If the email exists, a reset link has been sent"
    
    @staticmethod
    async def confirm_password_reset(
        db: AsyncSession, 
        token: str, 
        new_password: str
    ) -> bool:
        """Confirm password reset with token"""
        # Get user ID from reset token
        user_id = await redis_client.get(f"password_reset:{token}")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        user = await AuthService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Set new password
        user.set_password(new_password)
        user.failed_login_attempts = 0  # Reset failed attempts
        user.locked_until = None  # Unlock account
        await db.commit()
        
        # Delete reset token
        await redis_client.delete(f"password_reset:{token}")
        
        # Invalidate all refresh tokens for security
        await redis_client.delete(f"refresh_token:{user_id}")
        
        return True
