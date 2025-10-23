import asyncio
from contextlib import contextmanager, asynccontextmanager

from fastapi import FastAPI

from app.worker.broker import rmq_router
from app.routers.extract import extract_info_router
from app.routers.process import process_router

app = FastAPI(title="Bloocheck-api")

app.include_router(rmq_router)
app.include_router(process_router)
app.include_router(extract_info_router)


@app.get("/")
async def root():
    return {
        "status": "El servicio está en ejecución"
    }