# -*- coding: utf-8 -*-
"""Зберігання вмісту файлів — компонент StorageAdapter із діаграми компонентів.

Підтримано два режими (перемикач STORAGE_BACKEND у .env):

  disk — вміст лежить у теці server_storage (локальна розробка, етапи 2–3);
  db   — вміст лежить у таблиці file_blobs у PostgreSQL.

Режим «db» потрібен для публікації в інтернеті: на безкоштовних тарифах
хмарних провайдерів файлова система тимчасова й очищається при перезапуску,
тому файли, збережені на диску, зникали б, а записи в БД лишалися.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from server.config import STORAGE_BACKEND, STORAGE_DIR


def _user_dir(user_id: int) -> Path:
    path = STORAGE_DIR / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save(db: Session, user_id: int, file_id: int, stored_name: str, data: bytes) -> None:
    """Зберігає (або замінює) вміст файлу."""
    if STORAGE_BACKEND == "db":
        from server.models import FileBlob
        blob = db.get(FileBlob, file_id)
        if blob is None:
            db.add(FileBlob(file_id=file_id, data=data))
        else:
            blob.data = data
    else:
        (_user_dir(user_id) / stored_name).write_bytes(data)


def load(db: Session, user_id: int, file_id: int, stored_name: str) -> Optional[bytes]:
    """Повертає вміст файлу або None, якщо його немає у сховищі."""
    if STORAGE_BACKEND == "db":
        from server.models import FileBlob
        blob = db.get(FileBlob, file_id)
        return blob.data if blob else None
    path = _user_dir(user_id) / stored_name
    return path.read_bytes() if path.exists() else None


def delete(db: Session, user_id: int, file_id: int, stored_name: str) -> None:
    """Прибирає вміст файлу зі сховища."""
    if STORAGE_BACKEND == "db":
        from server.models import FileBlob
        blob = db.get(FileBlob, file_id)
        if blob is not None:
            db.delete(blob)
    else:
        path = _user_dir(user_id) / stored_name
        if path.exists():
            path.unlink()
