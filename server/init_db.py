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


def main() -> None:
    print("Підключення:", DATABASE_URL)
    Base.metadata.create_all(engine)
    print("Таблиці users і files створено (якщо їх не було).")

    with SessionLocal() as db:
        for login, full_name, password in DEMO_USERS:
            if db.scalar(select(User).where(User.login == login)) is None:
                db.add(User(login=login, full_name=full_name,
                            password_hash=hash_password(password)))
                print(f"  + користувач {login} / {password}")
        db.commit()
    print("Готово.")


if __name__ == "__main__":
    main()
