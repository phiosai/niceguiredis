from __future__ import annotations

import inspect
from contextlib import nullcontext
from typing import Any, Callable, Optional

from nicegui import background_tasks, ui

from core.pools import RedisPool, Unsubscribe


class RealtimeUpdater:
    """Attaches a per-client callback to a Redis channel and detaches it when the client goes away.

    The badge reflects the real state of the shared pub/sub listener. Browser websocket reconnects
    are handled by NiceGUI itself; the Redis side reconnects inside ``RedisPool``.
    """

    def __init__(
        self,
        redis: RedisPool,
        channel: str,
        update_callback: Callable[[str], Any],
        label: Optional[str] = None,
    ) -> None:
        self.redis = redis
        self.channel = channel
        self.update_callback = update_callback
        self.label = label
        self.container: Optional[ui.row] = None
        self.status_indicator: Optional[ui.badge] = None
        self._unsubscribe: Optional[Unsubscribe] = None
        self._closed = False

    def render(self, parent: Optional[ui.element] = None) -> ui.row:
        with parent if parent is not None else nullcontext():
            with ui.row().classes("items-center gap-2") as self.container:
                if self.label:
                    ui.label(self.label).classes("text-sm font-semibold")
                self.status_indicator = ui.badge("Connecting...", color="grey")
                ui.timer(1.0, self._refresh_status)

        ui.context.client.on_delete(self._close)
        background_tasks.create(self._subscribe(), name=f"subscribe {self.channel}")
        return self.container

    def _refresh_status(self) -> None:
        if self.status_indicator is None:
            return
        if self.redis.is_listening and self._unsubscribe is not None:
            self.status_indicator.set_text("Connected")
            self.status_indicator.props("color=positive")
        else:
            self.status_indicator.set_text("Disconnected")
            self.status_indicator.props("color=negative")

    async def _on_message(self, message: str) -> None:
        if self.container is None or self.container.is_deleted:
            return
        with self.container:  # gives the callback a UI context (e.g. for ui.notify)
            result = self.update_callback(message)
            if inspect.isawaitable(result):
                await result

    async def _subscribe(self) -> None:
        unsubscribe = await self.redis.subscribe(self.channel, self._on_message)
        if self._closed:  # client left while we were subscribing
            await unsubscribe()
        else:
            self._unsubscribe = unsubscribe

    async def _close(self) -> None:
        self._closed = True
        if self._unsubscribe is not None:
            await self._unsubscribe()
            self._unsubscribe = None
