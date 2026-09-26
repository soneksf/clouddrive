# -*- coding: utf-8 -*-
"""FileTableModel + FileListController — подання та логіка списку файлів."""
from __future__ import annotations

from typing import List

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from common.sort_filter import (FileMeta, SortField, SortFilterService, SortOrder,
                                TypeFilter)

# Стовпці таблиці кабінету. Стовпець «Назва» приховати не можна (вимога завдання).
COLUMNS = [
    ("Назва", SortField.NAME, False),
    ("Тип", SortField.EXTENSION, True),
    ("Розмір", None, True),
    ("Створено", SortField.CREATED_AT, True),
    ("Змінено", SortField.MODIFIED_AT, True),
    ("Хто завантажив", SortField.UPLOADED_BY, True),
    ("Хто редагував", SortField.MODIFIED_BY, True),
]


def human_size(size: int) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024 or unit == "ГБ":
            return f"{size:.0f} {unit}" if unit == "Б" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ГБ"


class FileTableModel(QAbstractTableModel):
    """Подання списку метаданих у вигляді таблиці."""

    def __init__(self, files: List[FileMeta] | None = None):
        super().__init__()
        self._files: List[FileMeta] = files or []

    def set_files(self, files: List[FileMeta]) -> None:
        self.beginResetModel()
        self._files = list(files)
        self.endResetModel()

    def file_at(self, row: int) -> FileMeta:
        return self._files[row]

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._files)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        f = self._files[index.row()]
        return [
            f.name,
            f.extension,
            human_size(f.size),
            f.created_at.strftime("%d.%m.%Y %H:%M:%S"),
            f.modified_at.strftime("%d.%m.%Y %H:%M:%S"),
            f.uploaded_by,
            f.modified_by,
        ][index.column()]

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return COLUMNS[section][0]


class FileListController:
    """Логіка списку: зберігає налаштування подання та застосовує їх до даних.

    Відповідає класу FileListController із VOPC-діаграми етапу 1.
    """

    def __init__(self, api_client):
        self.api = api_client
        self.sort_field: SortField = SortField.CREATED_AT   # поле за замовчуванням — варіант 1
        self.sort_order: SortOrder = SortOrder.DESC
        self.type_filter: TypeFilter = TypeFilter.ALL
        self.cache: List[FileMeta] = []

    def toggle_sort(self, field: SortField) -> None:
        """Клік по заголовку: те саме поле — перемикання напряму, інше — нове поле."""
        if field is self.sort_field:
            self.sort_order = self.sort_order.toggled()
        else:
            self.sort_field = field
            self.sort_order = SortOrder.ASC

    def set_filter(self, type_filter: TypeFilter) -> None:
        self.type_filter = type_filter

    def refresh(self) -> List[FileMeta]:
        """Запит до сервера і застосування поточних налаштувань подання."""
        self.cache = self.api.get_files(self.sort_field, self.sort_order, self.type_filter)
        return self.visible_files()

    def visible_files(self) -> List[FileMeta]:
        """Фільтрація й сортування кешу без звернення до сервера."""
        return SortFilterService.apply(self.cache, self.sort_field,
                                       self.sort_order, self.type_filter)
