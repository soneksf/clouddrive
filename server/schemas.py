# -*- coding: utf-8 -*-
"""Схеми запитів і відповідей REST API."""
from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    login: str
    password: str


class RegisterRequest(BaseModel):
    login: str
    password: str
    full_name: str = ""


class UserOut(BaseModel):
    id: int
    login: str
    full_name: str


class SessionOut(BaseModel):
    token: str
    user: UserOut


class FileOut(BaseModel):
    """Метадані файлу — рівно ті стовпці, що показує таблиця кабінету."""
    id: int
    name: str
    extension: str
    size: int
    created_at: datetime
    modified_at: datetime
    uploaded_by: str
    modified_by: str
    sha256: str


class MessageOut(BaseModel):
    detail: str
