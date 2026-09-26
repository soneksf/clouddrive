# -*- coding: utf-8 -*-
"""Прецедент «Авторизуватися» — серверна частина."""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.database import get_db
from server.models import User
from server.schemas import LoginRequest, RegisterRequest, SessionOut, UserOut
from server.security import create_token, decode_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def current_user(authorization: str = Header(default=""),
                 db: Session = Depends(get_db)) -> User:
    """Залежність: витягує користувача з токена «Authorization: Bearer ...»."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Потрібна авторизація")
    payload = decode_token(authorization[7:])
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недійсний або прострочений токен")
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Користувача не знайдено")
    return user


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.login == data.login))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Такий логін уже зайнятий")
    user = User(login=data.login, full_name=data.full_name or data.login,
                password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, login=user.login, full_name=user.full_name)


@router.post("/login", response_model=SessionOut)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.login == data.login))
    if user is None or not verify_password(data.password, user.password_hash):
        # 401 — гілка [невірні дані] на діаграмі послідовності етапу 1
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невірний логін або пароль")
    return SessionOut(
        token=create_token(user.id, user.login),
        user=UserOut(id=user.id, login=user.login, full_name=user.full_name),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return UserOut(id=user.id, login=user.login, full_name=user.full_name)
