"""Password hashing with bcrypt via passlib."""

from typing import cast

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password. Returns a bcrypt hash string."""
    return cast(str, pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hash. Returns True if match."""
    return cast(bool, pwd_context.verify(plain_password, hashed_password))
