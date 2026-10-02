from __future__ import annotations

from contextlib import nullcontext
from typing import Optional

from nicegui import ui


class CollapsiblePanel:
    """Card with a header toggle. Put children inside with ``with panel.content:``."""

    def __init__(self, title: str, default_open: bool = True) -> None:
        self.title = title
        self.is_open = default_open
        self.content: Optional[ui.column] = None
        self.toggle_button: Optional[ui.button] = None

    def render(self, parent: Optional[ui.element] = None) -> ui.card:
        with parent if parent is not None else nullcontext():
            with ui.card().classes("w-full") as card:
                with ui.row().classes("items-center justify-between w-full"):
                    ui.label(self.title).classes("text-lg font-semibold")
                    self.toggle_button = ui.button(icon=self._icon(), on_click=self.toggle).props("flat dense round")
                self.content = ui.column().classes("w-full")
                self.content.set_visibility(self.is_open)
        return card

    def _icon(self) -> str:
        return "expand_less" if self.is_open else "expand_more"

    def toggle(self) -> None:
        self.is_open = not self.is_open
        if self.content is not None:
            self.content.set_visibility(self.is_open)
        if self.toggle_button is not None:
            self.toggle_button.props(f"icon={self._icon()}")

    def add_content(self, element: ui.element) -> None:
        """Move an already-created element into the panel."""
        if self.content is not None:
            element.move(self.content)
