"""Router auth: register & token (JWT)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    email: str
    full_name: str | None = None


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, session: SessionDep) -> User:
    exists = (
        await session.execute(select(User).where(User.email == data.email))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    session.add(user)
    await session.commit()
    return user


@router.post("/token", response_model=TokenOut)
async def token(
    session: SessionDep,
    form: OAuth2PasswordRequestForm = Depends(),
) -> TokenOut:
    user = (
        await session.execute(select(User).where(User.email == form.username))
    ).scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email atau password salah")
    return TokenOut(access_token=create_access_token(user.email))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
