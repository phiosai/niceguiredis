from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time

from fastapi.responses import RedirectResponse
from nicegui import app, ui

from core.services import METRICS_CHANNEL, Services, create_services
from pages.admin import AdminPage
from pages.base import BasePage
from pages.dashboard import DashboardPage
from pages.long_task_demo import LongTaskDemoPage
from pages.realtime_metrics import RealTimeMetricsPage

logger = logging.getLogger(__name__)

PAGE_CLASSES: list[type[BasePage]] = [DashboardPage, RealTimeMetricsPage, LongTaskDemoPage, AdminPage]


def collect_system_metrics() -> float:
    return round(os.getloadavg()[0], 2)


async def background_metric_collector(services: Services, interval: float) -> None:
    """Store the latest sample in Redis and publish it for live pages."""
    while True:
        try:
            value = collect_system_metrics()
            await services.redis.set("metric:system", str(value))
            await services.redis.publish(
                METRICS_CHANNEL, json.dumps({"value": value, "source": "collector", "ts": time.time()})
            )
        except Exception as e:
            logger.warning("Metric collector error: %s", e)
        await asyncio.sleep(interval)


def create_app() -> Services:
    """Register pages and lifecycle hooks; returns the shared services (useful for tests)."""
    services = create_services()
    background: list[asyncio.Task] = []

    for page_cls in PAGE_CLASSES:
        page_cls.register(services)

    @ui.page("/")
    def index() -> RedirectResponse:
        return RedirectResponse("/dashboard")

    # Pass the coroutine functions themselves: NiceGUI awaits them, so shutdown really finishes
    # closing pools before the process exits (wrapping them in create_task would not).
    async def on_startup() -> None:
        await services.initialize()
        interval = float(os.getenv("METRICS_INTERVAL", "5"))
        background.append(asyncio.create_task(background_metric_collector(services, interval)))
        logger.info("Services initialized")

    async def on_shutdown() -> None:
        logger.info("Shutting down services...")
        for task in background:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await services.close()
        logger.info("Services closed")

    app.on_startup(on_startup)
    app.on_shutdown(on_shutdown)
    return services
