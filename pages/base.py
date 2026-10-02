from __future__ import annotations

from typing import ClassVar

from nicegui import ui

from core.services import Services

NAV_ITEMS: list[tuple[str, str]] = [
    ("Dashboard", "/dashboard"),
    ("Real-Time", "/realtime"),
    ("Long Task", "/long-task"),
    ("Admin", "/admin"),
]


class BasePage:
    """A page class is instantiated once per browser visit, so instance attributes are per-client state."""

    route: ClassVar[str]
    title: ClassVar[str]

    def __init__(self, services: Services) -> None:
        self.services = services

    @classmethod
    def register(cls, services: Services) -> None:
        @ui.page(cls.route, title=cls.title)
        def _page() -> None:
            page = cls(services)
            page.layout()
            with ui.column().classes("w-full max-w-6xl mx-auto p-4 gap-4"):
                page.build()

    def layout(self) -> None:
        with ui.header().classes("items-center justify-between px-4"):
            ui.label("Advanced NiceGUI App").classes("text-lg font-semibold")
            with ui.row().classes("gap-1"):
                for label, route in NAV_ITEMS:
                    button = ui.button(label, on_click=lambda r=route: ui.navigate.to(r)).props("flat color=white")
                    if route == self.route:
                        button.classes("bg-white/20")

    def build(self) -> None:
        raise NotImplementedError
