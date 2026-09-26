# -*- coding: utf-8 -*-
"""LoginDialog — прецедент «Авторизуватися» на боці клієнта."""
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel,
                               QLineEdit, QMessageBox, QVBoxLayout)

from client.api_client import ApiError, RestApiClient


class LoginDialog(QDialog):
    def __init__(self, api: RestApiClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("CloudDrive — вхід")
        self.setMinimumWidth(380)

        self.url_edit = QLineEdit(api.base_url)
        self.login_edit = QLineEdit("sofiia")
        self.password_edit = QLineEdit("qwerty123")
        self.password_edit.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Адреса сервера:", self.url_edit)
        form.addRow("Логін:", self.login_edit)
        form.addRow("Пароль:", self.password_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Увійти")
        buttons.button(QDialogButtonBox.Cancel).setText("Скасувати")
        buttons.accepted.connect(self.try_login)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Авторизація на віддаленому сервері"))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def try_login(self) -> None:
        self.api.base_url = self.url_edit.text().strip().rstrip("/")
        try:
            self.api.login(self.login_edit.text().strip(), self.password_edit.text())
        except ApiError as exc:
            QMessageBox.warning(self, "Помилка входу", str(exc))
            return
        self.accept()
