# -*- coding: utf-8 -*-
"""Тест 2 — визначення способу перегляду файлу (типи варіанта 1: .xml і .png)."""
import pytest

from common.file_types import PreviewKind, detect_preview_kind, extension_of, sha256_of_bytes


@pytest.mark.parametrize("name,expected", [
    ("report.xml", PreviewKind.TEXT),      # .xml показується як ТЕКСТ, не як розмітка
    ("REPORT.XML", PreviewKind.TEXT),      # регістр розширення не має значення
    ("photo.png", PreviewKind.IMAGE),      # .png показується як зображення
    ("notes.txt", PreviewKind.UNSUPPORTED),
    ("archive.zip", PreviewKind.UNSUPPORTED),
    ("README", PreviewKind.UNSUPPORTED),
])
def test_detect_preview_kind(name, expected):
    assert detect_preview_kind(name) is expected


def test_extension_is_lowercased():
    assert extension_of("Photo.PNG") == ".png"
    assert extension_of("no_extension") == ""


def test_sha256_is_stable_and_distinguishes_content():
    assert sha256_of_bytes(b"<root/>") == sha256_of_bytes(b"<root/>")
    assert sha256_of_bytes(b"<root/>") != sha256_of_bytes(b"<root></root>")
