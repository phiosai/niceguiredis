from __future__ import annotations

import asyncio
import logging

from nicegui import ui

from components.loading_spinner import LoadingSpinner
from components.metric_card import MetricCard
from pages.base import BasePage

logger = logging.getLogger(__name__)


class DashboardPage(BasePage):
    route = "/dashboard"
    title = "Dashboard"

    async def _load_metric(self, name: str) -> str | int:
        redis = self.services.redis
        postgres = self.services.postgres
        if name == "redis_keys":
            return await redis.dbsize()
        if name == "admin_rows":
            return await postgres.fetchval("SELECT COUNT(*) FROM admin_logs")
        if name == "system_load":
            return await redis.get("metric:system") or "—"
        raise KeyError(name)

    async def _refresh(self, *names: str) -> None:
        names = names or tuple(self.metrics)
        results = await asyncio.gather(*(self._load_metric(n) for n in names), return_exceptions=True)
        for name, result in zip(names, results):
            if isinstance(result, Exception):
                logger.warning("Loading %s failed: %s", name, result)
                self.metrics[name].update_value("error")
                ui.notify(f"{self.metrics[name].title}: {result}", type="negative")
            else:
                self.metrics[name].update_value(result)

    def build(self) -> None:
        ui.label("System Metrics").classes("text-2xl font-bold")
        spinner = LoadingSpinner(message="Loading metrics...")
        spinner.show()

        self.metrics: dict[str, MetricCard] = {}
        with ui.row().classes("gap-4 flex-wrap"):
            for name, title, subtitle, icon in (
                ("redis_keys", "Redis Keys", "DBSIZE of the configured Redis DB", "storage"),
                ("admin_rows", "Postgres Rows", "Rows in admin_logs", "table_rows"),
                ("system_load", "System Load", "1-min load avg (background collector)", "speed"),
            ):
                card = MetricCard(title, subtitle=subtitle, icon=icon,
                                  on_refresh=lambda n=name: self._refresh(n))
                card.render()
                self.metrics[name] = card

        async def initial_load() -> None:
            try:
                await self._refresh()
            finally:
                spinner.hide()

        # Timer callbacks run inside this page's UI context, unlike a bare asyncio.create_task.
        ui.timer(0, initial_load, once=True)
        ui.timer(10, self._refresh)
