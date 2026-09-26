# -*- coding: utf-8 -*-
"""CloudDrive REST API — серверна частина (етап 2).

Запуск:  uvicorn server.main:app --reload
Swagger: http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routers import auth, files

app = FastAPI(
    title="CloudDrive API",
    description="Сервер клієнта віддаленої папки (система типу 2, варіант 1)",
    version="1.0.0",
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


@app.get("/", tags=["service"])
def root():
    return {"service": "CloudDrive API", "docs": "/docs"}
