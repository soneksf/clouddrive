# -*- coding: utf-8 -*-
"""Створення таблиць у PostgreSQL і двох демонстраційних користувачів.

Запуск з кореня проєкту:  python -m server.init_db
"""
from sqlalchemy import select

from server.config import DATABASE_URL
from server.database import Base, SessionLocal, engine
from server.models import User  # noqa: F401  (потрібен для metadata)
from server.security import hash_password

DEMO_USERS = [
    ("sofiia", "Софія Власник", "qwerty123"),
    ("ivan", "Іван Колега", "qwerty123"),
]


def ensure_schema_and_users(verbose: bool = True) -> None:
    """Створює таблиці й демонстраційних користувачів. Безпечно викликати повторно."""
    Base.metadata.create_all(engine)
    if verbose:
        print("Таблиці створено (якщо їх не було).")
    with SessionLocal() as db:
        for login, full_name, password in DEMO_USERS:
            if db.scalar(select(User).where(User.login == login)) is None:
                db.add(User(login=login, full_name=full_name,
                            password_hash=hash_password(password)))
                if verbose:
                    print(f"  + користувач {login} / {password}")
        db.commit()


def main() -> None:
    print("Підключення:", DATABASE_URL)
    ensure_schema_and_users()
    print("Готово.")


if __name__ == "__main__":
    main()
