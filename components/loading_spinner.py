from __future__ import annotations

from contextlib import nullcontext
from typing import Optional

from nicegui import ui


class LoadingSpinner:
    """Spinner + message in its own container, so hiding it never hides the caller's layout."""

    def __init__(self, message: str = "Loading...", size: str = "2em", color: str = "primary") -> None:
        self.message = message
        self.size = size
        self.color = color
        self.container: Optional[ui.column] = None
        self.label: Optional[ui.label] = None

    def show(self, parent: Optional[ui.element] = None) -> None:
        """Create the spinner on first call (must run in a UI context), then just make it visible."""
        if self.container is None:
            with parent if parent is not None else nullcontext():
                self.container = ui.column().classes("items-center justify-center gap-2 w-full py-4")
                with self.container:
                    ui.spinner(size=self.size, color=self.color)
                    self.label = ui.label(self.message).classes("text-sm text-gray-600")
        self.container.set_visibility(True)

    def hide(self) -> None:
        if self.container is not None:
            self.container.set_visibility(False)

    def update_message(self, message: str) -> None:
        self.message = message
        if self.label is not None:
            self.label.text = message
