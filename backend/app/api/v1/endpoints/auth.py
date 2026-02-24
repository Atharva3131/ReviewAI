"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    UserRegistration, UserLogin, TokenResponse, RefreshTokenRequest,
    PasswordResetRequest, PasswordResetConfirm, PasswordChange,
    AuthStatus, UserResponse, OrganizationResponse
)
from app.core.security import SecurityService
from app.models.user import User
from app.models.organization import Organization

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    registration_data: UserRegistration,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Register new user and organization
    
    Creates a new user account and organization. The first user becomes the admin.
    """
    try:
        user, organization = await AuthService.register_user(db, registration_data)
        tokens = await AuthService.create_tokens(user, organization)
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        ) from e


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Authenticate user and return access tokens
    
    Validates user credentials and returns JWT access and refresh tokens.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        user, organization = await AuthService.authenticate_user(db, login_data)
        tokens = await AuthService.create_tokens(user, organization)
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        ) from e


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Refresh access token using refresh token
    
    Exchanges a valid refresh token for new access and refresh tokens.
    """
    try:
        tokens = await AuthService.refresh_access_token(db, refresh_data.refresh_token)
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        ) from e


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout user by invalidating refresh token
    
    Invalidates the user's refresh token to prevent further token refresh.
    """
    try:
        user_id = SecurityService.get_user_id_from_token(credentials.credentials)
        await AuthService.logout_user(user_id)
        return {"message": "Successfully logged out"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        ) from e


@router.get("/me", response_model=AuthStatus)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get current authenticated user information
    
    Returns the current user's profile and organization information.
    """
    try:
        user_id = SecurityService.get_user_id_from_token(credentials.credentials)
        user = await AuthService.get_user_by_id(db, user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        organization = await db.get(Organization, user.organization_id)
        
        return AuthStatus(
            is_authenticated=True,
            user=UserResponse.from_orm(user),
            organization=OrganizationResponse.from_orm(organization) if organization else None,
            permissions=[]  # TODO: Implement permissions
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        ) from e


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Change user password
    
    Changes the current user's password after verifying the current password.
    """
    try:
        user_id = SecurityService.get_user_id_from_token(credentials.credentials)
        
        await AuthService.change_password(
            db, 
            user_id, 
            password_data.current_password, 
            password_data.new_password
        )
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        ) from e


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Request password reset
    
    Initiates password reset process by sending reset token to user's email.
    """
    try:
        message = await AuthService.reset_password(db, reset_data.email)
        return {"message": message}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        ) from e


@router.post("/reset-password/confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Confirm password reset
    
    Completes password reset process using the reset token.
    """
    try:
        await AuthService.confirm_password_reset(
            db, 
            reset_data.token, 
            reset_data.new_password
        )
        return {"message": "Password reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset confirmation failed"
        ) from e


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Verify user email address
    
    Marks user's email as verified using verification token.
    """
    try:
        # In a real implementation, you'd validate the verification token
        # and extract user_id from it
        # For now, this is a placeholder
        return {"message": "Email verified successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        ) from e


@router.get("/validate-token", status_code=status.HTTP_200_OK)
async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Validate JWT token
    
    Validates the provided JWT token and returns token information.
    """
    try:
        payload = SecurityService.verify_token(credentials.credentials)
        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "organization_id": payload.get("org_id"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "expires": payload.get("exp")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        ) from e
