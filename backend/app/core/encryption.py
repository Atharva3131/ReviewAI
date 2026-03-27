"""
Data encryption service for at-rest and in-transit data protection
"""

import base64
import hashlib
import logging
import os
import secrets
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Custom encryption error"""

    pass


class DataEncryption:
    """Service for encrypting sensitive data at rest"""

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service

        Args:
            master_key: Master encryption key (base64 encoded)
        """
        if master_key:
            self.master_key = base64.urlsafe_b64decode(master_key.encode())
            self.fernet = Fernet(master_key.encode())
        else:
            # Generate a new master key if none provided
            key = Fernet.generate_key()
            self.fernet = Fernet(key)
            self.master_key = key

    @classmethod
    def generate_master_key(cls) -> str:
        """Generate a new master key"""
        key = Fernet.generate_key()
        return key.decode()

    def encrypt_string(self, plaintext: str) -> str:
        """
        Encrypt a string value

        Args:
            plaintext: String to encrypt

        Returns:
            Base64 encoded encrypted string
        """
        try:
            if not plaintext:
                return plaintext

            encrypted_bytes = self.fernet.encrypt(plaintext.encode("utf-8"))
            return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}")

    def decrypt_string(self, encrypted_text: str) -> str:
        """
        Decrypt a string value

        Args:
            encrypted_text: Base64 encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        try:
            if not encrypted_text:
                return encrypted_text

            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode("utf-8"))
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt data: {e}")

    def encrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a dictionary

        Args:
            data: Dictionary with data to encrypt

        Returns:
            Dictionary with encrypted sensitive fields
        """
        # Define sensitive fields that should be encrypted
        sensitive_fields = {
            "email",
            "phone",
            "address",
            "ssn",
            "credit_card",
            "password",
            "api_key",
            "token",
            "secret",
            "private_key",
        }

        encrypted_data = data.copy()

        for key, value in data.items():
            if isinstance(value, str) and any(
                field in key.lower() for field in sensitive_fields
            ):
                encrypted_data[key] = self.encrypt_string(value)
            elif isinstance(value, dict):
                encrypted_data[key] = self.encrypt_dict(value)

        return encrypted_data

    def decrypt_dict(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in a dictionary

        Args:
            encrypted_data: Dictionary with encrypted fields

        Returns:
            Dictionary with decrypted sensitive fields
        """
        sensitive_fields = {
            "email",
            "phone",
            "address",
            "ssn",
            "credit_card",
            "password",
            "api_key",
            "token",
            "secret",
            "private_key",
        }

        decrypted_data = encrypted_data.copy()

        for key, value in encrypted_data.items():
            if isinstance(value, str) and any(
                field in key.lower() for field in sensitive_fields
            ):
                try:
                    decrypted_data[key] = self.decrypt_string(value)
                except EncryptionError:
                    # If decryption fails, assume it's not encrypted
                    decrypted_data[key] = value
            elif isinstance(value, dict):
                decrypted_data[key] = self.decrypt_dict(value)

        return decrypted_data


class FieldLevelEncryption:
    """Field-level encryption for database columns"""

    def __init__(self, encryption_key: str):
        """
        Initialize field-level encryption

        Args:
            encryption_key: Base64 encoded encryption key
        """
        self.data_encryption = DataEncryption(encryption_key)

    def encrypt_field(self, value: Any, field_name: str) -> str:
        """
        Encrypt a database field value

        Args:
            value: Value to encrypt
            field_name: Name of the field (for logging)

        Returns:
            Encrypted value as string
        """
        if value is None:
            return None

        try:
            # Convert to string if not already
            str_value = str(value)
            encrypted = self.data_encryption.encrypt_string(str_value)

            logger.debug(f"Encrypted field {field_name}")
            return encrypted

        except Exception as e:
            logger.error(f"Failed to encrypt field {field_name}: {e}")
            raise EncryptionError(f"Field encryption failed for {field_name}")

    def decrypt_field(self, encrypted_value: str, field_name: str) -> str:
        """
        Decrypt a database field value

        Args:
            encrypted_value: Encrypted value
            field_name: Name of the field (for logging)

        Returns:
            Decrypted value
        """
        if encrypted_value is None:
            return None

        try:
            decrypted = self.data_encryption.decrypt_string(encrypted_value)
            logger.debug(f"Decrypted field {field_name}")
            return decrypted

        except Exception as e:
            logger.error(f"Failed to decrypt field {field_name}: {e}")
            raise EncryptionError(f"Field decryption failed for {field_name}")


class TransitEncryption:
    """Encryption for data in transit"""

    @staticmethod
    def generate_key_pair() -> tuple[bytes, bytes]:
        """
        Generate RSA key pair for asymmetric encryption

        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return private_pem, public_pem

    @staticmethod
    def encrypt_with_public_key(data: str, public_key_pem: bytes) -> str:
        """
        Encrypt data with RSA public key

        Args:
            data: Data to encrypt
            public_key_pem: Public key in PEM format

        Returns:
            Base64 encoded encrypted data
        """
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem, backend=default_backend()
            )

            encrypted = public_key.encrypt(
                data.encode("utf-8"),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            return base64.b64encode(encrypted).decode("utf-8")

        except Exception as e:
            logger.error(f"Public key encryption failed: {e}")
            raise EncryptionError(f"Transit encryption failed: {e}")

    @staticmethod
    def decrypt_with_private_key(encrypted_data: str, private_key_pem: bytes) -> str:
        """
        Decrypt data with RSA private key

        Args:
            encrypted_data: Base64 encoded encrypted data
            private_key_pem: Private key in PEM format

        Returns:
            Decrypted plaintext
        """
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem, password=None, backend=default_backend()
            )

            encrypted_bytes = base64.b64decode(encrypted_data.encode("utf-8"))

            decrypted = private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            return decrypted.decode("utf-8")

        except Exception as e:
            logger.error(f"Private key decryption failed: {e}")
            raise EncryptionError(f"Transit decryption failed: {e}")


class HashingService:
    """Service for secure hashing operations"""

    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """
        Hash password with salt using PBKDF2

        Args:
            password: Password to hash
            salt: Optional salt (generated if not provided)

        Returns:
            Tuple of (hashed_password, salt) both base64 encoded
        """
        if salt is None:
            salt = os.urandom(32)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )

        key = kdf.derive(password.encode("utf-8"))

        return (
            base64.b64encode(key).decode("utf-8"),
            base64.b64encode(salt).decode("utf-8"),
        )

    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify password against hash

        Args:
            password: Password to verify
            hashed_password: Base64 encoded hash
            salt: Base64 encoded salt

        Returns:
            True if password matches
        """
        try:
            salt_bytes = base64.b64decode(salt.encode("utf-8"))
            expected_hash = base64.b64decode(hashed_password.encode("utf-8"))

            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,
                backend=default_backend(),
            )

            kdf.verify(password.encode("utf-8"), expected_hash)
            return True

        except Exception:
            return False

    @staticmethod
    def hash_data(data: str, algorithm: str = "sha256") -> str:
        """
        Hash data with specified algorithm

        Args:
            data: Data to hash
            algorithm: Hash algorithm ('sha256', 'sha512', 'md5')

        Returns:
            Hexadecimal hash string
        """
        if algorithm == "sha256":
            return hashlib.sha256(data.encode("utf-8")).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(data.encode("utf-8")).hexdigest()
        elif algorithm == "md5":
            return hashlib.md5(data.encode("utf-8")).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generate cryptographically secure random token

        Args:
            length: Token length in bytes

        Returns:
            URL-safe base64 encoded token
        """
        return secrets.token_urlsafe(length)


class EncryptionKeyManager:
    """Manages encryption keys and key rotation"""

    def __init__(self, key_storage_path: str = None):
        """
        Initialize key manager

        Args:
            key_storage_path: Path to store encryption keys
        """
        self.key_storage_path = key_storage_path or os.getenv(
            "ENCRYPTION_KEY_PATH", "/tmp/keys"
        )
        self.ensure_key_directory()

    def ensure_key_directory(self):
        """Ensure key storage directory exists"""
        os.makedirs(self.key_storage_path, mode=0o700, exist_ok=True)

    def generate_and_store_key(self, key_name: str) -> str:
        """
        Generate and store a new encryption key

        Args:
            key_name: Name for the key

        Returns:
            Base64 encoded key
        """
        key = DataEncryption.generate_master_key()
        key_file = os.path.join(self.key_storage_path, f"{key_name}.key")

        # Store key with restricted permissions
        with open(key_file, "w") as f:
            f.write(key)

        os.chmod(key_file, 0o600)  # Read/write for owner only

        logger.info(f"Generated and stored encryption key: {key_name}")
        return key

    def load_key(self, key_name: str) -> Optional[str]:
        """
        Load encryption key from storage

        Args:
            key_name: Name of the key to load

        Returns:
            Base64 encoded key or None if not found
        """
        key_file = os.path.join(self.key_storage_path, f"{key_name}.key")

        try:
            with open(key_file, "r") as f:
                key = f.read().strip()

            logger.info(f"Loaded encryption key: {key_name}")
            return key

        except FileNotFoundError:
            logger.warning(f"Encryption key not found: {key_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to load encryption key {key_name}: {e}")
            raise EncryptionError(f"Key loading failed: {e}")

    def rotate_key(self, key_name: str) -> tuple[str, str]:
        """
        Rotate encryption key (generate new, keep old)

        Args:
            key_name: Name of the key to rotate

        Returns:
            Tuple of (new_key, old_key)
        """
        old_key = self.load_key(key_name)
        new_key = self.generate_and_store_key(key_name)

        # Store old key with timestamp
        if old_key:
            import time

            timestamp = int(time.time())
            old_key_file = os.path.join(
                self.key_storage_path, f"{key_name}.{timestamp}.old"
            )

            with open(old_key_file, "w") as f:
                f.write(old_key)

            os.chmod(old_key_file, 0o600)

        logger.info(f"Rotated encryption key: {key_name}")
        return new_key, old_key

    def list_keys(self) -> list[str]:
        """
        List all available encryption keys

        Returns:
            List of key names
        """
        try:
            key_files = [
                f.replace(".key", "")
                for f in os.listdir(self.key_storage_path)
                if f.endswith(".key")
            ]
            return key_files

        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return []


# Global encryption service instance
_encryption_service = None
_key_manager = None


def get_encryption_service() -> DataEncryption:
    """Get global encryption service instance"""
    global _encryption_service

    if _encryption_service is None:
        # Try to load master key from environment or key manager
        master_key = os.getenv("MASTER_ENCRYPTION_KEY")

        if not master_key:
            key_manager = get_key_manager()
            master_key = key_manager.load_key("master")

            if not master_key:
                # Generate new master key
                master_key = key_manager.generate_and_store_key("master")
                logger.warning("Generated new master encryption key")

        _encryption_service = DataEncryption(master_key)

    return _encryption_service


def get_key_manager() -> EncryptionKeyManager:
    """Get global key manager instance"""
    global _key_manager

    if _key_manager is None:
        _key_manager = EncryptionKeyManager()

    return _key_manager


# Convenience functions
def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data using global service"""
    return get_encryption_service().encrypt_string(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data using global service"""
    return get_encryption_service().decrypt_string(encrypted_data)
