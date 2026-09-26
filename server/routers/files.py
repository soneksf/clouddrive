# -*- coding: utf-8 -*-
"""Прецеденти роботи з файлами: список, завантаження, вивантаження, видалення."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from common.file_types import extension_of, sha256_of_bytes
from common.sort_filter import (FileMeta, SortFilterService, parse_sort_field,
                                parse_sort_order, parse_type_filter)
from server.config import MAX_UPLOAD_MB, STORAGE_DIR
from server.database import get_db
from server.models import FileEntry, User
from server.routers.auth import current_user
from server.schemas import FileOut, MessageOut

router = APIRouter(prefix="/api/files", tags=["files"])


def _to_meta(entry: FileEntry) -> FileMeta:
    return FileMeta(
        id=entry.id, name=entry.name, extension=entry.extension, size=entry.size,
        created_at=entry.created_at, modified_at=entry.modified_at,
        uploaded_by=entry.uploaded_by.full_name or entry.uploaded_by.login,
        modified_by=entry.modified_by.full_name or entry.modified_by.login,
        sha256=entry.sha256,
    )


def _user_dir(user: User):
    path = STORAGE_DIR / str(user.id)
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.get("", response_model=List[FileOut])
def list_files(sort: Optional[str] = Query(default="created_at"),
               order: Optional[str] = Query(default="desc"),
               type: Optional[str] = Query(default="all"),
               user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    """Список файлів кабінету з сортуванням і фільтром (операція варіанта 1).

    Сортування та фільтрація виконуються тим самим класом SortFilterService,
    що й на клієнті, — один алгоритм, один набір unit-тестів.
    """
    entries = db.scalars(select(FileEntry).where(FileEntry.owner_id == user.id)).all()
    metas = [_to_meta(e) for e in entries]
    result = SortFilterService.apply(
        metas,
        field=parse_sort_field(sort),
        order=parse_sort_order(order),
        type_filter=parse_type_filter(type),
    )
    return [FileOut(**m.__dict__) for m in result]


@router.post("", response_model=FileOut, status_code=201)
async def upload_file(file: UploadFile = File(...),
                      user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    """Завантаження файлу на сервер (у т. ч. через drag-and-drop у клієнті)."""
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"Файл більший за {MAX_UPLOAD_MB} МБ")

    name = file.filename
    entry = db.scalar(select(FileEntry).where(
        FileEntry.owner_id == user.id, FileEntry.name == name))
    now = datetime.utcnow()

    if entry is None:
        entry = FileEntry(owner_id=user.id, name=name, extension=extension_of(name),
                          created_at=now, modified_at=now,
                          uploaded_by_id=user.id, modified_by_id=user.id)
        db.add(entry)
        db.flush()                      # потрібен id для імені файлу у сховищі
        entry.stored_name = f"{entry.id}_{name}"
    else:
        # файл із такою назвою вже є — це нова версія
        entry.modified_at = now
        entry.modified_by_id = user.id

    entry.size = len(data)
    entry.sha256 = sha256_of_bytes(data)
    (_user_dir(user) / entry.stored_name).write_bytes(data)

    db.commit()
    db.refresh(entry)
    return FileOut(**_to_meta(entry).__dict__)


@router.get("/{file_id}/content")
def download_file(file_id: int,
                  user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    """Вивантаження файлу та перегляд вмісту (.xml як текст, .png як зображення)."""
    entry = db.get(FileEntry, file_id)
    if entry is None or entry.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файл не знайдено")
    path = _user_dir(user) / entry.stored_name
    if not path.exists():
        raise HTTPException(status.HTTP_410_GONE, "Вміст файлу відсутній у сховищі")
    return FileResponse(path, filename=entry.name)


@router.delete("/{file_id}", response_model=MessageOut)
def delete_file(file_id: int,
                user: User = Depends(current_user),
                db: Session = Depends(get_db)):
    entry = db.get(FileEntry, file_id)
    if entry is None or entry.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файл не знайдено")
    path = _user_dir(user) / entry.stored_name
    if path.exists():
        path.unlink()
    db.delete(entry)
    db.commit()
    return MessageOut(detail="Файл видалено")


@router.get("/health", include_in_schema=False)
def health():
    return Response(status_code=204)
