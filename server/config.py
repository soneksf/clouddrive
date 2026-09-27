# -*- coding: utf-8 -*-
"""Налаштування сервера. Читаються з файлу .env у корені проєкту."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_file()

# Рядок підключення до PostgreSQL.
# Хмарні провайдери (Neon, Render) видають URL у вигляді postgresql://...,
# а SQLAlchemy має знати драйвер — тому підставляємо +psycopg автоматично.
def _normalize(url: str) -> str:
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize(os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/clouddrive",
))

# Де зберігати вміст файлів: "disk" (локально) або "db" (публікація в інтернеті)
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "disk").strip().lower()

# Створювати таблиці й демо-користувачів при старті сервера (потрібно в хмарі)
INIT_DB_ON_START = os.environ.get("INIT_DB_ON_START", "0").strip() in ("1", "true", "yes")

# Тека, у якій сервер зберігає вміст файлів (вузол :FileStorage на діаграмі розгортання)
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", str(BASE_DIR / "server_storage")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
TOKEN_TTL_MINUTES = int(os.environ.get("TOKEN_TTL_MINUTES", "240"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "50"))
