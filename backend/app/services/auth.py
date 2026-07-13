"""AuthService — registration, login, token refresh."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AuthenticationError, ConflictError
from app.repositories.user import UserRepository
from app.security.jwt import create_access_token, create_refresh_token, decode_token
from app.security.password import hash_password, verify_password


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.user_repo = UserRepository(session)

    async def register(self, email: str, password: str, full_name: str) -> dict:
        existing = await self.user_repo.get_by_email(email)
        if existing is not None:
            raise ConflictError("Email already registered")

        user = await self.user_repo.create(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        }

    async def login(self, email: str, password: str) -> dict:
        user = await self.user_repo.get_by_email(email)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        user_id_str = str(user.id)
        return {
            "access_token": create_access_token(user_id_str, user.role),
            "refresh_token": create_refresh_token(user_id_str, user.role),
            "token_type": "bearer",
            "user": {
                "id": user_id_str,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            },
        }

    async def refresh(self, token: str) -> dict:
        try:
            payload = decode_token(token)
        except Exception as e:
            raise AuthenticationError("Invalid or expired refresh token") from e

        if payload.get("type") != "refresh":
            raise AuthenticationError("Refresh token required")

        user_id = payload["sub"]
        role = payload.get("role", "CUSTOMER")
        return {
            "access_token": create_access_token(user_id, role),
            "refresh_token": create_refresh_token(user_id, role),
            "token_type": "bearer",
        }

    async def get_me(self, user_id: uuid.UUID) -> dict:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found")
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "phone": user.phone,
            "default_address": user.default_address,
        }
