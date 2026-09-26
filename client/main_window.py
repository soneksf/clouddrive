# -*- coding: utf-8 -*-
"""MainWindow — головне вікно кабінету користувача (віртуальний диск)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout,
                               QHeaderView, QLabel, QMainWindow, QMenu, QMessageBox,
                               QPushButton, QSizePolicy, QSplitter, QStackedWidget,
                               QTableView, QTextEdit, QVBoxLayout, QWidget)

from client.api_client import ApiError, RestApiClient
from client.file_table import COLUMNS, FileListController, FileTableModel
from client.sync_dialog import SyncDialog
from common.file_types import PreviewKind, detect_preview_kind
from common.sort_filter import SortOrder, TypeFilter


class MainWindow(QMainWindow):
    def __init__(self, api: RestApiClient):
        super().__init__()
        self.api = api
        self.controller = FileListController(api)
        self.settings = QSettings("KNU", "CloudDrive")

        self.setWindowTitle(
            f"CloudDrive — кабінет користувача {api.session.full_name}")
        self.resize(1180, 640)
        self.setAcceptDrops(True)          # бонус: drag-and-drop завантаження

        self._build_ui()
        self._restore_columns()
        self.reload(from_server=True)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # ---- панель інструментів
        toolbar = self.addToolBar("Дії")
        toolbar.setMovable(False)

        act_upload = QAction("Завантажити на сервер", self)
        act_upload.triggered.connect(self.upload_files)
        act_download = QAction("Вивантажити на диск", self)
        act_download.triggered.connect(self.download_selected)
        act_delete = QAction("Видалити", self)
        act_delete.triggered.connect(self.delete_selected)
        act_refresh = QAction("Оновити", self)
        act_refresh.triggered.connect(lambda: self.reload(from_server=True))
        act_sync = QAction("Синхронізувати папку", self)
        act_sync.triggered.connect(self.open_sync)
        for action in (act_upload, act_download, act_delete, act_refresh, act_sync):
            toolbar.addAction(action)

        # ---- рядок фільтра та керування стовпцями (операція варіанта 1)
        top = QWidget()
        top.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(8, 6, 8, 6)
        top_layout.addWidget(QLabel("Фільтр:"))

        self.filter_box = QComboBox()
        self.filter_box.addItem("Усі файли", TypeFilter.ALL)
        self.filter_box.addItem("Лише .xml і .png", TypeFilter.XML_PNG_ONLY)
        self.filter_box.currentIndexChanged.connect(self.on_filter_changed)
        top_layout.addWidget(self.filter_box)

        self.columns_button = QPushButton("Стовпці")
        self.columns_menu = QMenu(self)
        self.columns_button.setMenu(self.columns_menu)
        top_layout.addWidget(self.columns_button)
        top_layout.addStretch(1)

        self.sort_label = QLabel()
        top_layout.addWidget(self.sort_label)

        # ---- таблиця
        self.table = QTableView()
        self.model = FileTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        self.table.clicked.connect(self.on_row_clicked)

        # ---- панель перегляду вмісту (.xml як текст, .png як зображення)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_image = QLabel("Оберіть файл .png")
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_hint = QLabel("Клікніть по файлу .xml або .png, щоб побачити вміст")
        self.preview_hint.setAlignment(Qt.AlignCenter)
        self.preview_hint.setWordWrap(True)

        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(self.preview_hint)    # 0
        self.preview_stack.addWidget(self.preview_text)    # 1
        self.preview_stack.addWidget(self.preview_image)   # 2

        preview_box = QWidget()
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(6, 6, 6, 6)
        self.preview_title = QLabel("Перегляд вмісту")
        self.preview_title.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_stack)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(preview_box)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(top, 0)
        layout.addWidget(splitter, 1)   # таблиця займає весь вільний простір
        self.setCentralWidget(central)

        self.statusBar().showMessage("Готово")

    def _restore_columns(self) -> None:
        """Пункти меню «Стовпці»: усі, крім стовпця з назвою."""
        self.columns_menu.clear()
        for index, (title, _field, hideable) in enumerate(COLUMNS):
            action = QAction(title, self, checkable=True)
            visible = self.settings.value(f"col_{index}", "1") == "1"
            action.setChecked(visible if hideable else True)
            action.setEnabled(hideable)
            action.toggled.connect(lambda checked, i=index: self.set_column_visible(i, checked))
            self.columns_menu.addAction(action)
            self.table.setColumnHidden(index, not action.isChecked())

    def set_column_visible(self, index: int, visible: bool) -> None:
        self.table.setColumnHidden(index, not visible)
        self.settings.setValue(f"col_{index}", "1" if visible else "0")

    # -------------------------------------------------------------- дані
    def reload(self, from_server: bool = False) -> None:
        try:
            files = self.controller.refresh() if from_server else self.controller.visible_files()
        except ApiError as exc:
            QMessageBox.critical(self, "Помилка", str(exc))
            return
        self.model.set_files(files)
        arrow = "▲" if self.controller.sort_order is SortOrder.ASC else "▼"
        field_title = next((t for t, f, _ in COLUMNS if f is self.controller.sort_field), "—")
        self.sort_label.setText(f"Сортування: {field_title} {arrow}   |   файлів: {len(files)}")
        self.table.resizeColumnsToContents()

    def on_header_clicked(self, section: int) -> None:
        field = COLUMNS[section][1]
        if field is None:                       # стовпець «Розмір» не сортується
            return
        self.controller.toggle_sort(field)
        self.reload(from_server=False)          # сортування по кешу, без запиту

    def on_filter_changed(self) -> None:
        self.controller.set_filter(self.filter_box.currentData())
        self.reload(from_server=False)

    # ------------------------------------------------------------ перегляд
    def on_row_clicked(self, index) -> None:
        meta = self.model.file_at(index.row())
        kind = detect_preview_kind(meta.name)
        self.preview_title.setText(f"Перегляд: {meta.name}")
        if kind is PreviewKind.UNSUPPORTED:
            self.preview_hint.setText(
                f"Формат {meta.extension or '—'} не передбачено варіантом 1.\n"
                "Переглядати можна лише .xml (як текст) і .png (як зображення).")
            self.preview_stack.setCurrentIndex(0)
            return
        try:
            data = self.api.download_bytes(meta.id)
        except ApiError as exc:
            QMessageBox.warning(self, "Помилка", str(exc))
            return
        if kind is PreviewKind.TEXT:
            # .xml показується саме як текст, а не як відрендерена розмітка
            self.preview_text.setPlainText(data.decode("utf-8", errors="replace"))
            self.preview_stack.setCurrentIndex(1)
        else:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.preview_image.setPixmap(pixmap.scaled(
                self.preview_image.width() or 400, 420,
                Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.preview_stack.setCurrentIndex(2)

    # --------------------------------------------------------------- дії
    def upload_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Оберіть файли для завантаження")
        self._upload_paths([Path(p) for p in paths])

    def _upload_paths(self, paths) -> None:
        if not paths:
            return
        sent = 0
        for path in paths:
            if not path.is_file():
                continue
            try:
                self.api.upload(path)
                sent += 1
            except ApiError as exc:
                QMessageBox.warning(self, "Помилка завантаження", f"{path.name}: {exc}")
        self.statusBar().showMessage(f"Завантажено файлів: {sent}", 5000)
        self.reload(from_server=True)

    def download_selected(self) -> None:
        rows = {i.row() for i in self.table.selectionModel().selectedRows()}
        if not rows:
            QMessageBox.information(self, "Вивантаження", "Оберіть хоча б один файл")
            return
        folder = QFileDialog.getExistingDirectory(self, "Куди зберегти")
        if not folder:
            return
        for row in rows:
            meta = self.model.file_at(row)
            try:
                self.api.download_to(meta.id, Path(folder) / meta.name)
            except ApiError as exc:
                QMessageBox.warning(self, "Помилка", f"{meta.name}: {exc}")
        self.statusBar().showMessage(f"Збережено у {folder}", 5000)

    def delete_selected(self) -> None:
        rows = {i.row() for i in self.table.selectionModel().selectedRows()}
        if not rows:
            return
        names = ", ".join(self.model.file_at(r).name for r in rows)
        answer = QMessageBox.question(self, "Видалення", f"Видалити: {names}?")
        if answer != QMessageBox.Yes:
            return
        for row in rows:
            meta = self.model.file_at(row)
            try:
                self.api.delete(meta.id)
            except ApiError as exc:
                QMessageBox.warning(self, "Помилка", f"{meta.name}: {exc}")
        self.reload(from_server=True)

    def open_sync(self) -> None:
        dialog = SyncDialog(self.api, self)
        dialog.exec()
        self.reload(from_server=True)

    # ------------------------------------------------------- drag-and-drop
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls()]
        self._upload_paths(paths)
        event.acceptProposedAction()
