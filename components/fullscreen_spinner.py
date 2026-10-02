from __future__ import annotations

from typing import Any, Callable, Optional

from nicegui import ui


class FullscreenSpinner:
    """Blocking overlay. Construct it while building the page; ``show``/``hide`` can then be called anywhere."""

    def __init__(self, message: str = "Loading...", on_cancel: Optional[Callable[[], Any]] = None) -> None:
        self.overlay = (
            ui.element("div")
            .classes("fixed inset-0 z-[6000] flex items-center justify-center")
            .style("background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(2px)")
        )
        with self.overlay:
            with ui.column().classes("items-center gap-4 bg-white p-8 rounded-lg shadow-lg"):
                ui.spinner(size="3em", color="primary")
                self.label = ui.label(message).classes("text-lg")
                if on_cancel is not None:
                    # Without this, the overlay would cover every other cancel button on the page.
                    ui.button("Cancel", on_click=on_cancel, color="negative")
        self.overlay.set_visibility(False)

    def show(self, message: Optional[str] = None) -> None:
        if message is not None:
            self.label.text = message
        self.overlay.set_visibility(True)

    def hide(self) -> None:
        self.overlay.set_visibility(False)
