# -*- coding: utf-8 -*-
"""SyncController + діалог синхронізації локальної та віддаленої папок."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QTextEdit,
                               QVBoxLayout)

from client.api_client import ApiError, RestApiClient
from common.file_types import ConflictStrategy, build_sync_plan, scan_local_folder
from common.sort_filter import SortField, SortOrder, TypeFilter


class SyncController:
    """Логіка синхронізації (див. діаграму активності етапу 1)."""

    def __init__(self, api: RestApiClient):
        self.api = api

    def plan(self, folder: Path, strategy: ConflictStrategy):
        local = scan_local_folder(folder)
        remote = self.api.get_files(SortField.NAME, SortOrder.ASC, TypeFilter.ALL)
        return build_sync_plan(local, remote, strategy), {f.name: f for f in remote}

    def execute(self, folder: Path, plan, remote_index) -> list[str]:
        log: list[str] = []
        for name in plan.upload:
            self.api.upload(folder / name)
            log.append(f"↑ завантажено на сервер: {name}")
        for name in plan.download:
            meta = remote_index[name]
            self.api.download_to(meta.id, folder / name)
            log.append(f"↓ вивантажено на диск: {name}")
        for name in plan.conflicts:
            log.append(f"! конфлікт (не змінювався): {name}")
        for name in plan.unchanged:
            log.append(f"= без змін: {name}")
        return log


class SyncDialog(QDialog):
    def __init__(self, api: RestApiClient, parent=None):
        super().__init__(parent)
        self.controller = SyncController(api)
        self.setWindowTitle("Синхронізація локальної та віддаленої папок")
        self.resize(720, 460)

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Оберіть локальну папку для синхронізації")
        browse = QPushButton("Огляд…")
        browse.clicked.connect(self.choose_folder)

        row = QHBoxLayout()
        row.addWidget(QLabel("Папка:"))
        row.addWidget(self.folder_edit, 1)
        row.addWidget(browse)

        self.strategy_box = QComboBox()
        self.strategy_box.addItem("Запитати про конфлікти", ConflictStrategy.ASK)
        self.strategy_box.addItem("Перемагає локальна копія", ConflictStrategy.PREFER_LOCAL)
        self.strategy_box.addItem("Перемагає віддалена копія", ConflictStrategy.PREFER_REMOTE)

        self.plan_button = QPushButton("Порівняти")
        self.plan_button.clicked.connect(self.build_plan)
        self.run_button = QPushButton("Виконати синхронізацію")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_sync)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Конфлікти:"))
        row2.addWidget(self.strategy_box, 1)
        row2.addWidget(self.plan_button)
        row2.addWidget(self.run_button)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addLayout(row2)
        layout.addWidget(self.log, 1)

        self._plan = None
        self._remote_index = {}

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Локальна папка")
        if folder:
            self.folder_edit.setText(folder)

    def _folder(self) -> Path | None:
        text = self.folder_edit.text().strip()
        if not text:
            QMessageBox.information(self, "Синхронізація", "Спочатку оберіть папку")
            return None
        return Path(text)

    def build_plan(self) -> None:
        folder = self._folder()
        if folder is None:
            return
        try:
            self._plan, self._remote_index = self.controller.plan(
                folder, self.strategy_box.currentData())
        except ApiError as exc:
            QMessageBox.critical(self, "Помилка", str(exc))
            return
        lines = ["План синхронізації: " + self._plan.summary(), ""]
        lines += [f"↑ {n}" for n in self._plan.upload]
        lines += [f"↓ {n}" for n in self._plan.download]
        lines += [f"! {n} — конфлікт, оберіть стратегію вище" for n in self._plan.conflicts]
        lines += [f"= {n}" for n in self._plan.unchanged]
        self.log.setPlainText("\n".join(lines))
        self.run_button.setEnabled(not self._plan.is_empty)

    def run_sync(self) -> None:
        folder = self._folder()
        if folder is None or self._plan is None:
            return
        try:
            log = self.controller.execute(folder, self._plan, self._remote_index)
        except (ApiError, OSError) as exc:
            QMessageBox.critical(self, "Помилка синхронізації", str(exc))
            return
        self.log.setPlainText("Синхронізацію виконано:\n\n" + "\n".join(log))
        self.run_button.setEnabled(False)
