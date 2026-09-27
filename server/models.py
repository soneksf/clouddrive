# -*- coding: utf-8 -*-
"""Моделі БД — реалізація доменної діаграми класів етапу 1."""
from datetime import datetime

from sqlalchemy import (BigInteger, DateTime, ForeignKey, Integer, LargeBinary, String,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base


class User(Base):
    """Користувач системи (клас «Користувач» доменної моделі)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    files: Mapped[list["FileEntry"]] = relationship(
        back_populates="owner", foreign_keys="FileEntry.owner_id",
        cascade="all, delete-orphan")

    def __repr__(self) -> str:  # зручно під час налагодження
        return f"<User {self.login}>"


class FileEntry(Base):
    """Метадані файлу у віртуальному диску користувача.

    Набір полів повністю покриває вимогу завдання до стовпців таблиці:
    назва, дата і час створення, дата і час зміни, хто завантажив, хто редагував.
    """
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_files_owner_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    modified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    modified_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="files", foreign_keys=[owner_id])
    uploaded_by: Mapped["User"] = relationship(foreign_keys=[uploaded_by_id])
    modified_by: Mapped["User"] = relationship(foreign_keys=[modified_by_id])

    def __repr__(self) -> str:
        return f"<FileEntry {self.name}>"


class FileBlob(Base):
    """Вміст файлу в БД. Використовується, коли STORAGE_BACKEND = "db"
    (публікація в інтернеті, де файлова система сервера тимчасова)."""
    __tablename__ = "file_blobs"

    file_id: Mapped[int] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
