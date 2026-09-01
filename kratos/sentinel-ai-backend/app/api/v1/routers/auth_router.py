"""
Minimum viable auth for a real demo: login, refresh, me, plus a role guard.
Deliberately small — Step 21 of the brief explicitly says not to build an
enterprise IAM here. RBAC is a single dependency factory over the 5 roles
already defined on the users model.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.database.session import get_db
from app.models import User
from app.models.enums import UserRole

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    email: str
    full_name: str


class RefreshRequest(BaseModel):
    refresh_token: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = (
        await db.execute(select(User).where(User.email == payload.get("sub")))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_roles(*roles: UserRole) -> Callable:
    """Route guard: `Depends(require_roles(UserRole.ADMIN))`."""

    async def dependency(user: User = Depends(get_current_user)) -> User:
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role.value}' is not permitted to access this resource",
            )
        return user

    return dependency


@router.post("/login", tags=["auth"], summary="Exchange email + password for a JWT", response_model=None)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = TokenResponse(
        access_token=create_access_token(user.email, user.role.value),
        refresh_token=create_refresh_token(user.email),
        role=user.role.value,
        email=user.email,
        full_name=user.full_name,
    )
    return {"data": token.model_dump(), "error": None}


@router.post("/refresh", tags=["auth"], summary="Exchange a refresh token for a new access token", response_model=None)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user = (
        await db.execute(select(User).where(User.email == payload.get("sub")))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return {
        "data": {
            "access_token": create_access_token(user.email, user.role.value),
            "token_type": "bearer",
        },
        "error": None,
    }


@router.get("/me", tags=["auth"], summary="Current authenticated user", response_model=None)
async def me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "employee_id": user.employee_id,
        },
        "error": None,
    }
