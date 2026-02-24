"""
Generate a secure SECRET_KEY for the application

Run this script to generate a cryptographically secure random key
for use in your .env file.

Usage:
    python generate_secret_key.py
"""
import secrets


def generate_secret_key(length: int = 32) -> str:
    """
    Generate a secure random secret key
    
    Args:
        length: Length of the key in bytes (default: 32)
        
    Returns:
        URL-safe base64-encoded random string
    """
    return secrets.token_urlsafe(length)


if __name__ == "__main__":
    print("=" * 60)
    print("SECRET KEY GENERATOR")
    print("=" * 60)
    print()
    print("Generated SECRET_KEY:")
    print()
    print(generate_secret_key())
    print()
    print("Copy this key and paste it into your backend/.env file")
    print("as the value for SECRET_KEY")
    print()
    print("=" * 60)
