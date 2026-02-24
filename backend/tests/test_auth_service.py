"""
Unit tests for authentication and authorization services
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.services.auth_service import AuthService
from app.core.security import SecurityService, TokenData
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.schemas.auth import UserRegistration, UserLogin, TokenResponse


class TestAuthService:
    """Test cases for AuthService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock organization
        self.mock_org = MagicMock(spec=Organization)
        self.mock_org.id = uuid.uuid4()
        self.mock_org.name = "Test Organization"
        self.mock_org.domain = "test.com"
        
        # Mock user
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = uuid.uuid4()
        self.mock_user.organization_id = self.mock_org.id
        self.mock_user.email = "test@example.com"
        self.mock_user.first_name = "John"
        self.mock_user.last_name = "Doe"
        self.mock_user.role = UserRole.USER
        self.mock_user.is_active = True
        self.mock_user.is_verified = False
        self.mock_user.is_locked = False
        self.mock_user.failed_login_attempts = 0
    
    @pytest.mark.asyncio
    async def test_register_user_success(self):
        """Test successful user registration"""
        registration_data = UserRegistration(
            email="newuser@example.com",
            password="SecurePassword123!",
            first_name="Jane",
            last_name="Smith",
            organization_name="New Organization",
            organization_domain="neworg.com"
        )
        
        # Mock database operations
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = None  # No existing user
        self.mock_db.add = MagicMock()
        self.mock_db.flush = AsyncMock()
        self.mock_db.commit = AsyncMock()
        self.mock_db.refresh = AsyncMock()
        
        # Mock organization and user creation
        mock_new_org = MagicMock()
        mock_new_org.id = uuid.uuid4()
        mock_new_user = MagicMock()
        mock_new_user.id = uuid.uuid4()
        mock_new_user.set_password = MagicMock()
        
        with patch('app.models.organization.Organization', return_value=mock_new_org), \
             patch('app.models.user.User', return_value=mock_new_user):
            
            user, organization = await AuthService.register_user(self.mock_db, registration_data)
            
            assert user == mock_new_user
            assert organization == mock_new_org
            mock_new_user.set_password.assert_called_once_with("SecurePassword123!")
            self.mock_db.add.assert_called()
            self.mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_email_exists(self):
        """Test user registration with existing email"""
        registration_data = UserRegistration(
            email="existing@example.com",
            password="SecurePassword123!",
            first_name="Jane",
            last_name="Smith",
            organization_name="New Organization"
        )
        
        # Mock existing user
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = self.mock_user
        
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.register_user(self.mock_db, registration_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test successful user authentication"""
        login_data = UserLogin(
            email="test@example.com",
            password="correct_password"
        )
        
        # Mock user lookup
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = self.mock_user
        self.mock_user.verify_password.return_value = True
        self.mock_user.reset_failed_login = MagicMock()
        self.mock_db.get.return_value = self.mock_org
        self.mock_db.commit = AsyncMock()
        
        user, organization = await AuthService.authenticate_user(self.mock_db, login_data)
        
        assert user == self.mock_user
        assert organization == self.mock_org
        self.mock_user.verify_password.assert_called_once_with("correct_password")
        self.mock_user.reset_failed_login.assert_called_once()
        self.mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        login_data = UserLogin(
            email="nonexistent@example.com",
            password="password"
        )
        
        # Mock no user found
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.authenticate_user(self.mock_db, login_data)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        login_data = UserLogin(
            email="test@example.com",
            password="wrong_password"
        )
        
        # Mock user lookup and wrong password
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = self.mock_user
        self.mock_user.verify_password.return_value = False
        self.mock_user.increment_failed_login = MagicMock()
        self.mock_db.commit = AsyncMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.authenticate_user(self.mock_db, login_data)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in exc_info.value.detail
        self.mock_user.increment_failed_login.assert_called_once()
        self.mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_locked_account(self):
        """Test authentication with locked account"""
        login_data = UserLogin(
            email="test@example.com",
            password="password"
        )
        
        # Mock locked user
        self.mock_user.is_locked = True
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = self.mock_user
        
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.authenticate_user(self.mock_db, login_data)
        
        assert exc_info.value.status_code == status.HTTP_423_LOCKED
        assert "temporarily locked" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_authenticate_user_inactive_account(self):
        """Test authentication with inactive account"""
        login_data = UserLogin(
            email="test@example.com",
            password="password"
        )
        
        # Mock inactive user
        self.mock_user.is_active = False
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = self.mock_user
        
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.authenticate_user(self.mock_db, login_data)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "deactivated" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_create_tokens_success(self):
        """Test successful token creation"""
        with patch('app.core.security.SecurityService.create_access_token', return_value="access_token"), \
             patch('app.core.security.SecurityService.create_refresh_token', return_value="refresh_token"), \
             patch('app.core.redis.redis_client.set', new_callable=AsyncMock), \
             patch('app.schemas.auth.UserResponse.from_orm', return_value={"id": str(self.mock_user.id)}), \
             patch('app.schemas.auth.OrganizationResponse.from_orm', return_value={"id": str(self.mock_org.id)}), \
             patch('app.core.config.settings') as mock_settings:
            
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            
            token_response = await AuthService.create_tokens(self.mock_user, self.mock_org)
            
            assert isinstance(token_response, TokenResponse)
            assert token_response.access_token == "access_token"
            assert token_response.refresh_token == "refresh_token"
            assert token_response.expires_in == 30 * 60  # 30 minutes in seconds
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self):
        """Test successful access token refresh"""
        refresh_token = "valid_refresh_token"
        user_id = str(self.mock_user.id)
        
        # Mock token verification
        mock_payload = {
            "sub": user_id,
            "type": "refresh"
        }
        
        with patch('app.core.security.SecurityService.verify_token', return_value=mock_payload), \
             patch('app.core.redis.redis_client.get', return_value=refresh_token), \
             patch.object(AuthService, 'create_tokens', return_value=MagicMock()) as mock_create_tokens:
            
            self.mock_db.get.side_effect = [self.mock_user, self.mock_org]
            
            result = await AuthService.refresh_access_token(self.mock_db, refresh_token)
            
            mock_create_tokens.assert_called_once_with(self.mock_user, self.mock_org)
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self):
        """Test access token refresh with invalid token"""
        with patch('app.core.security.SecurityService.verify_token', side_effect=Exception("Invalid token")):
            with pytest.raises(HTTPException) as exc_info:
                await AuthService.refresh_access_token(self.mock_db, "invalid_token")
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid refresh token" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_not_in_redis(self):
        """Test access token refresh when token not in Redis"""
        refresh_token = "valid_refresh_token"
        user_id = str(self.mock_user.id)
        
        mock_payload = {
            "sub": user_id,
            "type": "refresh"
        }
        
        with patch('app.core.security.SecurityService.verify_token', return_value=mock_payload), \
             patch('app.core.redis.redis_client.get', return_value=None):  # Token not in Redis
            
            with pytest.raises(HTTPException) as exc_info:
                await AuthService.refresh_access_token(self.mock_db, refresh_token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "not found or expired" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_logout_user_success(self):
        """Test successful user logout"""
        user_id = str(self.mock_user.id)
        
        with patch('app.core.redis.redis_client.delete', return_value=True):
            result = await AuthService.logout_user(user_id)
            assert result == True
    
    @pytest.mark.asyncio
    async def test_logout_user_failure(self):
        """Test user logout failure"""
        user_id = str(self.mock_user.id)
        
        with patch('app.core.redis.redis_client.delete', side_effect=Exception("Redis error")):
            result = await AuthService.logout_user(user_id)
            assert result == False
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self):
        """Test successful user retrieval by email"""
        email = "test@example.com"
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = self.mock_user
        
        result = await AuthService.get_user_by_email(self.mock_db, email)
        
        assert result == self.mock_user
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self):
        """Test user retrieval by email when not found"""
        email = "nonexistent@example.com"
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await AuthService.get_user_by_email(self.mock_db, email)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self):
        """Test successful user retrieval by ID"""
        user_id = str(self.mock_user.id)
        self.mock_db.get.return_value = self.mock_user
        
        result = await AuthService.get_user_by_id(self.mock_db, user_id)
        
        assert result == self.mock_user
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_invalid_uuid(self):
        """Test user retrieval by invalid UUID"""
        invalid_id = "invalid-uuid"
        
        result = await AuthService.get_user_by_id(self.mock_db, invalid_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_verify_user_email_success(self):
        """Test successful email verification"""
        user_id = str(self.mock_user.id)
        self.mock_db.get.return_value = self.mock_user
        self.mock_db.commit = AsyncMock()
        
        result = await AuthService.verify_user_email(self.mock_db, user_id)
        
        assert result == True
        assert self.mock_user.is_verified == True
        self.mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_user_email_user_not_found(self):
        """Test email verification when user not found"""
        user_id = str(uuid.uuid4())
        self.mock_db.get.return_value = None
        
        result = await AuthService.verify_user_email(self.mock_db, user_id)
        
        assert result == False
    
    @pytest.mark.asyncio
    async def test_change_password_success(self):
        """Test successful password change"""
        user_id = str(self.mock_user.id)
        current_password = "old_password"
        new_password = "new_password"
        
        self.mock_db.get.return_value = self.mock_user
        self.mock_user.verify_password.return_value = True
        self.mock_user.set_password = MagicMock()
        self.mock_db.commit = AsyncMock()
        
        with patch('app.core.redis.redis_client.delete'):
            result = await AuthService.change_password(
                self.mock_db, user_id, current_password, new_password
            )
            
            assert result == True
            self.mock_user.verify_password.assert_called_once_with(current_password)
            self.mock_user.set_password.assert_called_once_with(new_password)
            self.mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self):
        """Test password change when user not found"""
        user_id = str(uuid.uuid4())
        self.mock_db.get.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.change_password(
                self.mock_db, user_id, "old_password", "new_password"
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current_password(self):
        """Test password change with wrong current password"""
        user_id = str(self.mock_user.id)
        self.mock_db.get.return_value = self.mock_user
        self.mock_user.verify_password.return_value = False
        
        with pytest.raises(HTTPException) as exc_info:
            await AuthService.change_password(
                self.mock_db, user_id, "wrong_password", "new_password"
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Current password is incorrect" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        """Test successful password reset initiation"""
        email = "test@example.com"
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = self.mock_user
        
        with patch('app.core.security.SecurityService.generate_password_reset_token', return_value="reset_token"), \
             patch('app.core.redis.redis_client.set'):
            
            result = await AuthService.reset_password(self.mock_db, email)
            
            assert "reset link has been sent" in result
    
    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self):
        """Test password reset with non-existent user"""
        email = "nonexistent@example.com"
        self.mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await AuthService.reset_password(self.mock_db, email)
        
        # Should still return success message for security
        assert "reset link has been sent" in result
    
    @pytest.mark.asyncio
    async def test_confirm_password_reset_success(self):
        """Test successful password reset confirmation"""
        token = "valid_reset_token"
        new_password = "new_password"
        user_id = str(self.mock_user.id)
        
        self.mock_db.get.return_value = self.mock_user
        self.mock_user.set_password = MagicMock()
        self.mock_db.commit = AsyncMock()
        
        with patch('app.core.redis.redis_client.get', return_value=user_id), \
             patch('app.core.redis.redis_client.delete'):
            
            result = await AuthService.confirm_password_reset(
                self.mock_db, token, new_password
            )
            
            assert result == True
            self.mock_user.set_password.assert_called_once_with(new_password)
            assert self.mock_user.failed_login_attempts == 0
            assert self.mock_user.locked_until is None
            self.mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_confirm_password_reset_invalid_token(self):
        """Test password reset confirmation with invalid token"""
        token = "invalid_token"
        new_password = "new_password"
        
        with patch('app.core.redis.redis_client.get', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await AuthService.confirm_password_reset(
                    self.mock_db, token, new_password
                )
            
            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid or expired" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_confirm_password_reset_user_not_found(self):
        """Test password reset confirmation when user not found"""
        token = "valid_token"
        new_password = "new_password"
        user_id = str(uuid.uuid4())
        
        self.mock_db.get.return_value = None
        
        with patch('app.core.redis.redis_client.get', return_value=user_id):
            with pytest.raises(HTTPException) as exc_info:
                await AuthService.confirm_password_reset(
                    self.mock_db, token, new_password
                )
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "User not found" in exc_info.value.detail


class TestSecurityService:
    """Test cases for SecurityService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.test_data = {
            "user_id": "user-123",
            "organization_id": "org-123",
            "email": "test@example.com",
            "role": "user"
        }
    
    def test_create_access_token_success(self):
        """Test successful access token creation"""
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test_secret_key"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            
            token = SecurityService.create_access_token(self.test_data)
            
            assert isinstance(token, str)
            assert len(token) > 0
    
    def test_create_access_token_with_custom_expiry(self):
        """Test access token creation with custom expiry"""
        custom_expiry = timedelta(minutes=60)
        
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test_secret_key"
            
            token = SecurityService.create_access_token(self.test_data, custom_expiry)
            
            assert isinstance(token, str)
            assert len(token) > 0
    
    def test_create_refresh_token_success(self):
        """Test successful refresh token creation"""
        user_id = "user-123"
        
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test_secret_key"
            
            token = SecurityService.create_refresh_token(user_id)
            
            assert isinstance(token, str)
            assert len(token) > 0
    
    def test_verify_token_success(self):
        """Test successful token verification"""
        # First create a token
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test_secret_key"
            
            token = SecurityService.create_access_token(self.test_data)
            payload = SecurityService.verify_token(token)
            
            assert payload["user_id"] == "user-123"
            assert payload["organization_id"] == "org-123"
            assert payload["email"] == "test@example.com"
            assert payload["role"] == "user"
            assert "exp" in payload
            assert "iat" in payload
            assert "jti" in payload
    
    def test_verify_token_invalid_token(self):
        """Test token verification with invalid token"""
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test_secret_key"
            
            with pytest.raises(Exception):  # Should raise JWTError or similar
                SecurityService.verify_token("invalid_token")
    
    def test_verify_token_expired_token(self):
        """Test token verification with expired token"""
        # Create token with past expiry
        past_expiry = timedelta(minutes=-30)
        
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test_secret_key"
            
            token = SecurityService.create_access_token(self.test_data, past_expiry)
            
            with pytest.raises(Exception):  # Should raise JWTError for expired token
                SecurityService.verify_token(token)
    
    def test_verify_token_wrong_secret(self):
        """Test token verification with wrong secret key"""
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test_secret_key"
            token = SecurityService.create_access_token(self.test_data)
            
            # Change secret key
            mock_settings.SECRET_KEY = "different_secret_key"
            
            with pytest.raises(Exception):  # Should raise JWTError
                SecurityService.verify_token(token)


class TestTokenData:
    """Test cases for TokenData class"""
    
    def test_token_data_creation(self):
        """Test TokenData creation"""
        token_data = TokenData(
            user_id="user-123",
            organization_id="org-123",
            email="test@example.com",
            role="admin"
        )
        
        assert token_data.user_id == "user-123"
        assert token_data.organization_id == "org-123"
        assert token_data.email == "test@example.com"
        assert token_data.role == "admin"
    
    def test_token_data_to_dict(self):
        """Test TokenData to_dict method"""
        token_data = TokenData(
            user_id="user-123",
            organization_id="org-123",
            email="test@example.com",
            role="admin"
        )
        
        data_dict = token_data.to_dict()
        
        assert isinstance(data_dict, dict)
        assert data_dict["user_id"] == "user-123"
        assert data_dict["organization_id"] == "org-123"
        assert data_dict["email"] == "test@example.com"
        assert data_dict["role"] == "admin"


class TestPasswordSecurity:
    """Test cases for password security functions"""
    
    def test_password_hashing_and_verification(self):
        """Test password hashing and verification"""
        from app.core.security import pwd_context
        
        password = "SecurePassword123!"
        
        # Hash password
        hashed = pwd_context.hash(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plain text
        
        # Verify correct password
        assert pwd_context.verify(password, hashed) == True
        
        # Verify wrong password
        assert pwd_context.verify("WrongPassword", hashed) == False
    
    def test_password_hashing_different_results(self):
        """Test that same password produces different hashes (salt)"""
        from app.core.security import pwd_context
        
        password = "SecurePassword123!"
        
        hash1 = pwd_context.hash(password)
        hash2 = pwd_context.hash(password)
        
        # Should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert pwd_context.verify(password, hash1) == True
        assert pwd_context.verify(password, hash2) == True


class TestAuthenticationIntegration:
    """Integration tests for authentication flow"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_db = AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_full_authentication_flow(self):
        """Test complete authentication flow from registration to login"""
        # Mock registration
        registration_data = UserRegistration(
            email="integration@example.com",
            password="SecurePassword123!",
            first_name="Integration",
            last_name="Test",
            organization_name="Integration Org"
        )
        
        # Mock user and organization
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "integration@example.com"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.verify_password.return_value = True
        mock_user.reset_failed_login = MagicMock()
        
        mock_org = MagicMock()
        mock_org.id = uuid.uuid4()
        mock_org.name = "Integration Org"
        
        # Mock database operations
        self.mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing user during registration
            mock_user  # User found during login
        ]
        self.mock_db.add = MagicMock()
        self.mock_db.flush = AsyncMock()
        self.mock_db.commit = AsyncMock()
        self.mock_db.refresh = AsyncMock()
        self.mock_db.get.return_value = mock_org
        
        # Test registration
        with patch('app.models.organization.Organization', return_value=mock_org), \
             patch('app.models.user.User', return_value=mock_user):
            
            registered_user, registered_org = await AuthService.register_user(
                self.mock_db, registration_data
            )
            
            assert registered_user == mock_user
            assert registered_org == mock_org
        
        # Test login
        login_data = UserLogin(
            email="integration@example.com",
            password="SecurePassword123!"
        )
        
        authenticated_user, authenticated_org = await AuthService.authenticate_user(
            self.mock_db, login_data
        )
        
        assert authenticated_user == mock_user
        assert authenticated_org == mock_org
        mock_user.verify_password.assert_called_once_with("SecurePassword123!")
        mock_user.reset_failed_login.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_token_refresh_flow(self):
        """Test token refresh flow"""
        user_id = str(uuid.uuid4())
        
        # Create initial tokens
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = True
        
        mock_org = MagicMock()
        mock_org.id = str(uuid.uuid4())
        
        with patch('app.core.security.SecurityService.create_access_token', return_value="access_token"), \
             patch('app.core.security.SecurityService.create_refresh_token', return_value="refresh_token"), \
             patch('app.core.redis.redis_client.set'), \
             patch('app.schemas.auth.UserResponse.from_orm', return_value={"id": user_id}), \
             patch('app.schemas.auth.OrganizationResponse.from_orm', return_value={"id": mock_org.id}), \
             patch('app.core.config.settings') as mock_settings:
            
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            
            # Create tokens
            token_response = await AuthService.create_tokens(mock_user, mock_org)
            refresh_token = token_response.refresh_token
            
            # Test token refresh
            mock_payload = {
                "sub": user_id,
                "type": "refresh"
            }
            
            self.mock_db.get.side_effect = [mock_user, mock_org]
            
            with patch('app.core.security.SecurityService.verify_token', return_value=mock_payload), \
                 patch('app.core.redis.redis_client.get', return_value=refresh_token), \
                 patch.object(AuthService, 'create_tokens', return_value=token_response) as mock_create_tokens:
                
                refreshed_tokens = await AuthService.refresh_access_token(
                    self.mock_db, refresh_token
                )
                
                assert refreshed_tokens == token_response
                mock_create_tokens.assert_called_once_with(mock_user, mock_org)


class TestAuthorizationHelpers:
    """Test cases for authorization helper functions"""
    
    def test_role_hierarchy(self):
        """Test user role hierarchy"""
        # Test role comparison if implemented
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        
        # Add more role-based tests as needed
    
    def test_permission_checking(self):
        """Test permission checking logic"""
        # This would test any permission checking functions
        # that might be implemented in the security module
        pass


# Helper functions for test data
def create_test_user_data():
    """Helper to create test user data"""
    return {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "role": UserRole.USER,
        "is_active": True,
        "is_verified": False
    }

def create_test_organization_data():
    """Helper to create test organization data"""
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Organization",
        "domain": "test.com",
        "settings": {}
    }

def create_test_registration_data():
    """Helper to create test registration data"""
    return UserRegistration(
        email="test@example.com",
        password="SecurePassword123!",
        first_name="Test",
        last_name="User",
        organization_name="Test Organization",
        organization_domain="test.com"
    )

def create_test_login_data():
    """Helper to create test login data"""
    return UserLogin(
        email="test@example.com",
        password="SecurePassword123!"
    )