# -*- coding: utf-8 -*-
"""Тест 4 — планування синхронізації локальної та віддаленої папок."""
from dataclasses import dataclass
from datetime import datetime

from common.file_types import ConflictStrategy, LocalFile, build_sync_plan


@dataclass
class RemoteStub:
    """Мінімальна заглушка віддаленого файлу (потрібні лише name і sha256)."""
    name: str
    sha256: str


def local(name: str, digest: str) -> LocalFile:
    return LocalFile(name=name, size=10, modified_at=datetime(2026, 5, 1), sha256=digest)


def test_file_only_on_disk_goes_to_upload():
    plan = build_sync_plan([local("new.xml", "aaa")], [])
    assert plan.upload == ["new.xml"] and not plan.download


def test_file_only_on_server_goes_to_download():
    plan = build_sync_plan([], [RemoteStub("remote.png", "bbb")])
    assert plan.download == ["remote.png"] and not plan.upload


def test_identical_files_are_skipped():
    plan = build_sync_plan([local("same.xml", "ccc")], [RemoteStub("same.xml", "ccc")])
    assert plan.unchanged == ["same.xml"]
    assert plan.is_empty


def test_different_content_is_conflict_by_default():
    plan = build_sync_plan([local("doc.xml", "ccc")], [RemoteStub("doc.xml", "ddd")])
    assert plan.conflicts == ["doc.xml"]


def test_conflict_strategy_prefer_local():
    plan = build_sync_plan([local("doc.xml", "ccc")], [RemoteStub("doc.xml", "ddd")],
                           ConflictStrategy.PREFER_LOCAL)
    assert plan.upload == ["doc.xml"] and not plan.conflicts


def test_conflict_strategy_prefer_remote():
    plan = build_sync_plan([local("doc.xml", "ccc")], [RemoteStub("doc.xml", "ddd")],
                           ConflictStrategy.PREFER_REMOTE)
    assert plan.download == ["doc.xml"] and not plan.conflicts


def test_mixed_folders_summary():
    plan = build_sync_plan(
        [local("a.xml", "1"), local("b.png", "2"), local("c.txt", "3")],
        [RemoteStub("b.png", "2"), RemoteStub("d.xml", "4")],
    )
    assert sorted(plan.upload) == ["a.xml", "c.txt"]
    assert plan.download == ["d.xml"]
    assert plan.unchanged == ["b.png"]
