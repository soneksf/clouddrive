# -*- coding: utf-8 -*-
"""SortFilterService — операція персонального варіанта 1.

Варіант 1:
  * сортування за датою і часом створення (за зростанням і спаданням);
  * фільтр: усі файли або лише файли типів .xml і .png.

Модуль свідомо не залежить ані від Qt, ані від бази даних — тому його
використовують і сервер, і десктоп-клієнт, і unit-тести (етап 2).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable, List, Optional

# Типи файлів персонального варіанта 1
VARIANT_EXTENSIONS = (".xml", ".png")


class SortField(str, Enum):
    """Поле сортування (див. переліки на діаграмі класів етапу 1)."""
    NAME = "name"
    CREATED_AT = "created_at"
    MODIFIED_AT = "modified_at"
    UPLOADED_BY = "uploaded_by"
    MODIFIED_BY = "modified_by"
    EXTENSION = "extension"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

    def toggled(self) -> "SortOrder":
        return SortOrder.DESC if self is SortOrder.ASC else SortOrder.ASC


class TypeFilter(str, Enum):
    ALL = "all"
    XML_PNG_ONLY = "xml_png"


@dataclass
class FileMeta:
    """Метадані одного файлу віртуального диска."""
    id: int
    name: str
    extension: str
    size: int
    created_at: datetime
    modified_at: datetime
    uploaded_by: str
    modified_by: str
    sha256: str = ""

    @property
    def is_variant_type(self) -> bool:
        return self.extension.lower() in VARIANT_EXTENSIONS


class SortFilterService:
    """Чиста логіка сортування та фільтрації списку метаданих."""

    @staticmethod
    def filter_by_type(files: Iterable[FileMeta], type_filter: TypeFilter) -> List[FileMeta]:
        """Фільтр варіанта 1: усі файли або лише .xml та .png."""
        items = list(files)
        if type_filter is TypeFilter.ALL:
            return items
        return [f for f in items if f.extension.lower() in VARIANT_EXTENSIONS]

    @staticmethod
    def sort(files: Iterable[FileMeta], field: SortField, order: SortOrder) -> List[FileMeta]:
        """Сортування за довільним полем; ключове для варіанта — CREATED_AT."""
        items = list(files)

        def key(f: FileMeta):
            value = getattr(f, field.value)
            if isinstance(value, str):
                return value.lower()
            return value

        return sorted(items, key=key, reverse=(order is SortOrder.DESC))

    @staticmethod
    def sort_by_created_at(files: Iterable[FileMeta], order: SortOrder) -> List[FileMeta]:
        """Операція варіанта 1 у чистому вигляді."""
        return SortFilterService.sort(files, SortField.CREATED_AT, order)

    @staticmethod
    def apply(files: Iterable[FileMeta],
              field: SortField = SortField.CREATED_AT,
              order: SortOrder = SortOrder.DESC,
              type_filter: TypeFilter = TypeFilter.ALL) -> List[FileMeta]:
        """Повний конвеєр: спочатку фільтрація, потім сортування.

        Саме такий порядок зображено на діаграмі активності етапу 1:
        фільтр зменшує обсяг даних, які потім сортуються.
        """
        return SortFilterService.sort(
            SortFilterService.filter_by_type(files, type_filter), field, order)


def parse_sort_field(value: Optional[str]) -> SortField:
    try:
        return SortField(value) if value else SortField.CREATED_AT
    except ValueError:
        return SortField.CREATED_AT


def parse_sort_order(value: Optional[str]) -> SortOrder:
    try:
        return SortOrder(value) if value else SortOrder.DESC
    except ValueError:
        return SortOrder.DESC


def parse_type_filter(value: Optional[str]) -> TypeFilter:
    try:
        return TypeFilter(value) if value else TypeFilter.ALL
    except ValueError:
        return TypeFilter.ALL
