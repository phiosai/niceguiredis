from __future__ import annotations

import json
import random
from datetime import datetime

from nicegui import ui

from components.realtime_updater import RealtimeUpdater
from core.services import METRICS_CHANNEL
from pages.base import BasePage


class RealTimeMetricsPage(BasePage):
    route = "/realtime"
    title = "Real-Time Metrics"

    def _handle_update(self, message: str) -> None:
        try:
            data = json.loads(message)
            value = data.get("value", 0)
            source = data.get("source", "unknown")
        except (json.JSONDecodeError, AttributeError):
            value, source = message, "raw"
        self.value_label.text = f"Current Value: {value}"
        self.meta_label.text = f"from {source} at {datetime.now():%H:%M:%S}"
        self.history.push(f"{datetime.now():%H:%M:%S}  {source}: {value}")

    def build(self) -> None:
        ui.label("Real-Time Metrics").classes("text-2xl font-bold")
        redis = self.services.redis

        with ui.card().classes("p-4"):
            self.value_label = ui.label("Current Value: —").classes("text-xl font-bold")
            self.meta_label = ui.label("waiting for messages...").classes("text-xs text-gray-500")

        self.history = ui.log(max_lines=50).classes("w-full h-48")

        RealtimeUpdater(redis, METRICS_CHANNEL, self._handle_update, label="Live updates").render()

        async def publish_test() -> None:
            payload = json.dumps({"value": random.randint(1, 100), "source": "button"})
            try:
                receivers = await redis.publish(METRICS_CHANNEL, payload)
                ui.notify(f"Published to {receivers} subscriber connection(s)")
            except Exception as e:
                ui.notify(f"Publish failed: {e}", type="negative")

        ui.button("Publish Test Update", on_click=publish_test)
        ui.label(
            f"Tip: open this page in two tabs, or run: redis-cli PUBLISH {METRICS_CHANNEL} '{{\"value\": 42}}'"
        ).classes("text-xs text-gray-500")
