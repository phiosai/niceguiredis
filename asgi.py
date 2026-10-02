"""Mount the app on your own FastAPI instance.

    uvicorn asgi:fastapi_app --host 0.0.0.0 --port 8080

Run ONE worker per process: NiceGUI keeps per-client UI state and websockets in memory, so
``--workers N`` would break sessions. Scale out with several processes behind a load balancer
that uses sticky sessions instead.
"""
from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from nicegui import ui

load_dotenv()

from core.app_factory import create_app  # noqa: E402

logging.basicConfig(level=logging.INFO)

fastapi_app = FastAPI()


@fastapi_app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


create_app()
ui.run_with(fastapi_app, title="Advanced NiceGUI App")
