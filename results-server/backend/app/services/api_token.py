"""API Token service for CRUD operations and authentication."""

import secrets
from datetime import datetime, timezone
from typing import Optional, Sequence

from passlib.hash import argon2
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApiToken, User
from app.schemas.api_token import ApiTokenCreate


class ApiTokenService:
    """Service for API Token operations."""

    TOKEN_PREFIX = "bp_"  # BenchPro token prefix
    TOKEN_LENGTH = 32  # Length of random part

    def generate_token(self) -> str:
        """Generate a new random token."""
        random_part = secrets.token_urlsafe(self.TOKEN_LENGTH)
        return f"{self.TOKEN_PREFIX}{random_part}"

    def hash_token(self, token: str) -> str:
        """Hash a token for storage."""
        return argon2.hash(token)

    def verify_token(self, token: str, token_hash: str) -> bool:
        """Verify a token against its hash."""
        try:
            return argon2.verify(token, token_hash)
        except Exception:
            return False

    async def get(self, db: AsyncSession, id: int) -> Optional[ApiToken]:
        """Get a token by ID."""
        result = await db.execute(select(ApiToken).where(ApiToken.id == id))
        return result.scalar_one_or_none()

    async def get_by_user(
        self, db: AsyncSession, user_id: int
    ) -> Sequence[ApiToken]:
        """Get all tokens for a user."""
        result = await db.execute(
            select(ApiToken)
            .where(ApiToken.user_id == user_id)
            .order_by(ApiToken.created_at.desc())
        )
        return result.scalars().all()

    async def create(
        self, db: AsyncSession, *, user_id: int, obj_in: ApiTokenCreate
    ) -> tuple[ApiToken, str]:
        """Create a new token.

        Returns tuple of (token_record, plain_text_token).
        The plain text token is only available at creation time.
        """
        plain_token = self.generate_token()
        token_hash = self.hash_token(plain_token)

        db_token = ApiToken(
            user_id=user_id,
            name=obj_in.name,
            token_hash=token_hash,
        )
        db.add(db_token)
        await db.commit()
        await db.refresh(db_token)

        return db_token, plain_token

    async def revoke(self, db: AsyncSession, *, id: int) -> Optional[ApiToken]:
        """Revoke a token by setting revoked_at."""
        token = await self.get(db, id)
        if token and token.revoked_at is None:
            token.revoked_at = datetime.now(timezone.utc)
            db.add(token)
            await db.commit()
            await db.refresh(token)
        return token

    async def authenticate(
        self, db: AsyncSession, token: str
    ) -> Optional[User]:
        """Authenticate a request using a token.

        Returns the user if token is valid and not revoked, None otherwise.
        """
        # Get all non-revoked tokens and check each
        # In production, consider caching or indexed lookup
        result = await db.execute(
            select(ApiToken)
            .where(ApiToken.revoked_at.is_(None))
            .options()  # Could add joinedload for user
        )
        tokens = result.scalars().all()

        for api_token in tokens:
            if self.verify_token(token, api_token.token_hash):
                # Load and return the user
                user_result = await db.execute(
                    select(User).where(User.id == api_token.user_id)
                )
                return user_result.scalar_one_or_none()

        return None


# Singleton instance
api_token_service = ApiTokenService()

