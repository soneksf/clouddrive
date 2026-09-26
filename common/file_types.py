# -*- coding: utf-8 -*-
"""Визначення способу перегляду файлу та планування синхронізації."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Iterable, List


class PreviewKind(str, Enum):
    """Як відображати вміст файлу при кліку (варіант 1: .xml і .png)."""
    TEXT = "text"        # .xml — показується як текст, а не як розмітка
    IMAGE = "image"      # .png — показується як зображення
    UNSUPPORTED = "unsupported"


def detect_preview_kind(file_name: str) -> PreviewKind:
    ext = os.path.splitext(file_name)[1].lower()
    if ext == ".xml":
        return PreviewKind.TEXT
    if ext == ".png":
        return PreviewKind.IMAGE
    return PreviewKind.UNSUPPORTED


def extension_of(file_name: str) -> str:
    return os.path.splitext(file_name)[1].lower()


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------- синхронізація
@dataclass
class LocalFile:
    name: str
    size: int
    modified_at: datetime
    sha256: str


class ConflictStrategy(str, Enum):
    ASK = "ask"                  # запитати користувача
    PREFER_LOCAL = "local"       # перемагає локальна копія
    PREFER_REMOTE = "remote"     # перемагає віддалена копія


@dataclass
class SyncPlan:
    """Результат порівняння локальної та віддаленої папок."""
    upload: List[str] = field(default_factory=list)
    download: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    unchanged: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.upload or self.download or self.conflicts)

    def summary(self) -> str:
        return ("завантажити на сервер: {}, вивантажити на диск: {}, "
                "конфліктів: {}, без змін: {}").format(
            len(self.upload), len(self.download), len(self.conflicts), len(self.unchanged))


def build_sync_plan(local_files: Iterable[LocalFile],
                    remote_files: Iterable,
                    strategy: ConflictStrategy = ConflictStrategy.ASK) -> SyncPlan:
    """Порівнює два набори файлів за назвою і хешем.

    remote_files — будь-які об'єкти з атрибутами name, sha256 (наприклад FileMeta).
    Логіка відповідає діаграмі активності «Синхронізація» етапу 1.
    """
    local: Dict[str, LocalFile] = {f.name: f for f in local_files}
    remote: Dict[str, object] = {f.name: f for f in remote_files}
    plan = SyncPlan()

    for name, lf in local.items():
        rf = remote.get(name)
        if rf is None:
            plan.upload.append(name)          # файл є лише локально
        elif lf.sha256 == getattr(rf, "sha256", ""):
            plan.unchanged.append(name)       # копії збігаються
        else:
            # вміст різний — це конфлікт, який вирішує обрана стратегія
            if strategy is ConflictStrategy.PREFER_LOCAL:
                plan.upload.append(name)
            elif strategy is ConflictStrategy.PREFER_REMOTE:
                plan.download.append(name)
            else:
                plan.conflicts.append(name)

    for name in remote:
        if name not in local:
            plan.download.append(name)        # файл є лише на сервері

    return plan


def scan_local_folder(folder: Path) -> List[LocalFile]:
    """Сканує локальну папку (без рекурсії) і повертає метадані файлів."""
    result: List[LocalFile] = []
    if not folder.exists():
        return result
    for entry in sorted(folder.iterdir()):
        if entry.is_file():
            stat = entry.stat()
            result.append(LocalFile(
                name=entry.name,
                size=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                sha256=sha256_of_file(entry),
            ))
    return result
