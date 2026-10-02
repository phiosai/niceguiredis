from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from nicegui import ui

load_dotenv()  # before create_app() so services see .env values

from core.app_factory import create_app  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

create_app()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Advanced NiceGUI App",
        reload=os.getenv("NICEGUI_RELOAD", "false").lower() == "true",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        show=False,
    )
