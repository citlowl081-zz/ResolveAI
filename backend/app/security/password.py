"""Password hashing with bcrypt via passlib."""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password. Returns a bcrypt hash string."""
    result: object = pwd_context.hash(password)
    if not isinstance(result, str):
        raise TypeError(
            f"Password hashing returned unexpected type: {type(result).__name__}"
        )
    return result


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hash. Returns True if match."""
    result: object = pwd_context.verify(plain_password, hashed_password)
    if not isinstance(result, bool):
        raise TypeError(
            f"Password verification returned unexpected type: {type(result).__name__}"
        )
    return result
