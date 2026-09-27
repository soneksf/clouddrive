# -*- coding: utf-8 -*-
"""CloudDrive REST API — серверна частина (етап 2).

Запуск:  uvicorn server.main:app --reload
Swagger: http://127.0.0.1:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from server.config import BASE_DIR, INIT_DB_ON_START
from server.routers import auth, files


@asynccontextmanager
async def lifespan(app: FastAPI):
    """У хмарі (INIT_DB_ON_START=1) таблиці й демо-користувачі створюються
    автоматично під час першого запуску сервера."""
    if INIT_DB_ON_START:
        from server.init_db import ensure_schema_and_users
        ensure_schema_and_users(verbose=True)
    yield

app = FastAPI(
    title="CloudDrive API",
    description="Сервер клієнта віддаленої папки (система типу 2, варіант 1)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS знадобиться на етапі 3 для веб-клієнта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(files.router)


@app.get("/api", tags=["service"])
def api_root():
    """Службова перевірка: чи працює API."""
    return {"service": "CloudDrive API", "docs": "/docs", "web": "/web/"}


@app.get("/", include_in_schema=False)
def root():
    """Корінь сайту відкриває веб-клієнт (етап 3)."""
    return RedirectResponse(url="/web/login.html")


# Веб-клієнт: статичні сторінки HTML/CSS/JS (етап 3).
# Та сама серверна частина обслуговує і десктоп-клієнт, і веб-версію.
app.mount("/web", StaticFiles(directory=str(BASE_DIR / "web"), html=True), name="web")
