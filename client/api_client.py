# -*- coding: utf-8 -*-
"""RestApiClient — клас «boundary» із діаграми класів етапу 1.

Єдине місце в клієнті, яке знає про HTTP та адресу сервера.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests

from common.sort_filter import FileMeta, SortField, SortOrder, TypeFilter

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


class ApiError(Exception):
    """Помилка звернення до сервера з людським повідомленням."""


@dataclass
class Session:
    token: str
    user_id: int
    login: str
    full_name: str


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", ""))


class RestApiClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session: Optional[Session] = None

    # ------------------------------------------------------------- службове
    @property
    def _headers(self) -> dict:
        if self.session is None:
            return {}
        return {"Authorization": f"Bearer {self.session.token}"}

    def _handle(self, response: requests.Response):
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ApiError(f"{response.status_code}: {detail}")
        return response

    # ------------------------------------------------------------ авторизація
    def login(self, login: str, password: str) -> Session:
        try:
            response = requests.post(f"{self.base_url}/api/auth/login",
                                     json={"login": login, "password": password},
                                     timeout=self.timeout)
        except requests.RequestException as exc:
            raise ApiError(f"Сервер недоступний: {exc}") from exc
        data = self._handle(response).json()
        self.session = Session(token=data["token"], user_id=data["user"]["id"],
                               login=data["user"]["login"],
                               full_name=data["user"]["full_name"])
        return self.session

    def logout(self) -> None:
        self.session = None

    # ----------------------------------------------------------------- файли
    def get_files(self,
                  field: SortField = SortField.CREATED_AT,
                  order: SortOrder = SortOrder.DESC,
                  type_filter: TypeFilter = TypeFilter.ALL) -> List[FileMeta]:
        params = {"sort": field.value, "order": order.value, "type": type_filter.value}
        try:
            response = requests.get(f"{self.base_url}/api/files", params=params,
                                    headers=self._headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ApiError(f"Сервер недоступний: {exc}") from exc
        rows = self._handle(response).json()
        return [FileMeta(id=r["id"], name=r["name"], extension=r["extension"],
                         size=r["size"], created_at=_parse_dt(r["created_at"]),
                         modified_at=_parse_dt(r["modified_at"]),
                         uploaded_by=r["uploaded_by"], modified_by=r["modified_by"],
                         sha256=r["sha256"]) for r in rows]

    def upload(self, path: Path) -> FileMeta:
        with open(path, "rb") as fh:
            files = {"file": (path.name, fh, "application/octet-stream")}
            try:
                response = requests.post(f"{self.base_url}/api/files", files=files,
                                         headers=self._headers, timeout=60)
            except requests.RequestException as exc:
                raise ApiError(f"Сервер недоступний: {exc}") from exc
        r = self._handle(response).json()
        return FileMeta(id=r["id"], name=r["name"], extension=r["extension"],
                        size=r["size"], created_at=_parse_dt(r["created_at"]),
                        modified_at=_parse_dt(r["modified_at"]),
                        uploaded_by=r["uploaded_by"], modified_by=r["modified_by"],
                        sha256=r["sha256"])

    def download_bytes(self, file_id: int) -> bytes:
        try:
            response = requests.get(f"{self.base_url}/api/files/{file_id}/content",
                                    headers=self._headers, timeout=60)
        except requests.RequestException as exc:
            raise ApiError(f"Сервер недоступний: {exc}") from exc
        return self._handle(response).content

    def download_to(self, file_id: int, target: Path) -> Path:
        target.write_bytes(self.download_bytes(file_id))
        return target

    def delete(self, file_id: int) -> None:
        try:
            response = requests.delete(f"{self.base_url}/api/files/{file_id}",
                                       headers=self._headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ApiError(f"Сервер недоступний: {exc}") from exc
        self._handle(response)
