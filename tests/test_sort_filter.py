# -*- coding: utf-8 -*-
"""Тест 1 — ІНДИВІДУАЛЬНА ОПЕРАЦІЯ ВАРІАНТА 1.

Сортування за датою і часом створення (зростання/спадання)
та фільтр «усі файли / лише .xml, .png».
"""
from datetime import datetime

import pytest

from common.sort_filter import (FileMeta, SortFilterService, SortField, SortOrder,
                                TypeFilter)


def meta(name: str, created: str, ext: str = "") -> FileMeta:
    moment = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
    return FileMeta(id=abs(hash(name)) % 1000, name=name,
                    extension=ext or name[name.rfind("."):],
                    size=100, created_at=moment, modified_at=moment,
                    uploaded_by="sofiia", modified_by="sofiia")


@pytest.fixture
def sample():
    """Навмисно перемішаний набір: порядок у списку не збігається з датами."""
    return [
        meta("report.xml", "2026-03-15 10:00:00"),
        meta("photo.png", "2026-01-02 08:30:00"),
        meta("notes.txt", "2026-05-20 16:45:00"),
        meta("scheme.png", "2026-02-11 12:00:00"),
        meta("archive.zip", "2026-04-01 09:15:00"),
    ]


def test_sort_by_created_at_ascending(sample):
    """Сортування за датою створення за зростанням."""
    result = SortFilterService.sort_by_created_at(sample, SortOrder.ASC)
    assert [f.name for f in result] == [
        "photo.png", "scheme.png", "report.xml", "archive.zip", "notes.txt"]
    assert all(result[i].created_at <= result[i + 1].created_at
               for i in range(len(result) - 1))


def test_sort_by_created_at_descending(sample):
    """Сортування за датою створення за спаданням (режим за замовчуванням)."""
    result = SortFilterService.sort_by_created_at(sample, SortOrder.DESC)
    assert [f.name for f in result] == [
        "notes.txt", "archive.zip", "report.xml", "scheme.png", "photo.png"]


def test_filter_xml_png_only(sample):
    """Фільтр варіанта 1: у списку лишаються тільки .xml і .png."""
    result = SortFilterService.filter_by_type(sample, TypeFilter.XML_PNG_ONLY)
    assert {f.name for f in result} == {"report.xml", "photo.png", "scheme.png"}
    assert all(f.is_variant_type for f in result)


def test_filter_all_keeps_everything(sample):
    """Режим «усі файли» не втрачає жодного запису."""
    result = SortFilterService.filter_by_type(sample, TypeFilter.ALL)
    assert len(result) == len(sample)


def test_apply_filter_then_sort(sample):
    """Повний конвеєр операції варіанта: спочатку фільтр, потім сортування."""
    result = SortFilterService.apply(sample, SortField.CREATED_AT,
                                     SortOrder.DESC, TypeFilter.XML_PNG_ONLY)
    assert [f.name for f in result] == ["report.xml", "scheme.png", "photo.png"]


def test_sort_order_toggling():
    """Повторний клік по заголовку стовпця перемикає напрям сортування."""
    assert SortOrder.ASC.toggled() is SortOrder.DESC
    assert SortOrder.DESC.toggled() is SortOrder.ASC


def test_sort_does_not_mutate_source(sample):
    """Сортування повертає новий список і не псує вихідні дані."""
    original = [f.name for f in sample]
    SortFilterService.sort_by_created_at(sample, SortOrder.ASC)
    assert [f.name for f in sample] == original
