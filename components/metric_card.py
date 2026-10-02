from __future__ import annotations

from contextlib import nullcontext
from typing import Any, Callable, Optional

from nicegui import ui


class MetricCard:
    """Card showing a single value, with an optional (sync or async) refresh handler."""

    def __init__(
        self,
        title: str,
        value: str | int | float = "—",
        subtitle: Optional[str] = None,
        icon: Optional[str] = None,
        on_refresh: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.icon = icon
        self.on_refresh = on_refresh
        self.card: Optional[ui.card] = None
        self.value_label: Optional[ui.label] = None

    def render(self, parent: Optional[ui.element] = None) -> ui.card:
        with parent if parent is not None else nullcontext():
            with ui.card().classes("p-4 min-w-[220px]") as self.card:
                with ui.row().classes("items-center justify-between w-full no-wrap"):
                    ui.label(self.title).classes("text-sm font-semibold text-gray-600")
                    if self.on_refresh is not None:
                        # NiceGUI awaits async handlers itself and keeps the UI context (needed for ui.notify).
                        ui.button(icon="refresh", on_click=self.on_refresh).props("flat dense round")
                with ui.row().classes("items-center gap-2"):
                    if self.icon:
                        ui.icon(self.icon).classes("text-2xl text-primary")
                    self.value_label = ui.label(str(self.value)).classes("text-2xl font-bold")
                if self.subtitle:
                    ui.label(self.subtitle).classes("text-xs text-gray-500")
        return self.card

    def update_value(self, value: str | int | float) -> None:
        self.value = value
        if self.value_label is not None:
            self.value_label.text = str(value)
