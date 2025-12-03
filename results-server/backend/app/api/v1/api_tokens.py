"""API Token management endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.api_token import (
    ApiTokenCreate,
    ApiTokenCreated,
    ApiTokenList,
    ApiTokenRead,
)
from app.services import api_token_service

router = APIRouter()


@router.get("", response_model=ApiTokenList)
async def list_tokens(
    db: DbSession,
    current_user: CurrentUser,
) -> ApiTokenList:
    """List all API tokens for the current user."""
    tokens = await api_token_service.get_by_user(db, current_user.id)
    return ApiTokenList(tokens=[ApiTokenRead.model_validate(t) for t in tokens])


@router.post("", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_token(
    db: DbSession,
    current_user: CurrentUser,
    token_in: ApiTokenCreate,
) -> ApiTokenCreated:
    """Create a new API token.

    The plain-text token is only shown once in this response.
    Store it securely - it cannot be retrieved again.
    """
    db_token, plain_token = await api_token_service.create(
        db, user_id=current_user.id, obj_in=token_in
    )

    return ApiTokenCreated(
        id=db_token.id,
        name=db_token.name,
        created_at=db_token.created_at,
        revoked_at=db_token.revoked_at,
        token=plain_token,
    )


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    db: DbSession,
    current_user: CurrentUser,
    token_id: int,
) -> None:
    """Revoke an API token.

    Only the token owner can revoke their tokens.
    """
    token = await api_token_service.get(db, token_id)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    if token.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke another user's token",
        )

    if token.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is already revoked",
        )

    await api_token_service.revoke(db, id=token_id)

