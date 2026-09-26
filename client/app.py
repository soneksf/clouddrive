# -*- coding: utf-8 -*-
"""Точка входу десктоп-клієнта CloudDrive.

Запуск з кореня проєкту:  python -m client.app
"""
import sys

from PySide6.QtWidgets import QApplication, QDialog

from client.api_client import RestApiClient
from client.login_dialog import LoginDialog
from client.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("CloudDrive")

    api = RestApiClient()
    dialog = LoginDialog(api)
    if dialog.exec() != QDialog.Accepted:
        return 0                      # користувач скасував вхід

    window = MainWindow(api)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
