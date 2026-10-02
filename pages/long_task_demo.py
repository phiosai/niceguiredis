from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Awaitable, Callable, Optional

from nicegui import ui

from components.fullscreen_spinner import FullscreenSpinner
from pages.base import BasePage

LONG_TASK_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "long_task.py"


class LongTaskDemoPage(BasePage):
    route = "/long-task"
    title = "Long Task Demo"

    def __init__(self, services) -> None:
        super().__init__(services)
        self.task: Optional[asyncio.Task] = None

    def _duration(self) -> int:
        return max(1, min(60, int(self.duration_input.value or 10)))

    def _set_progress(self, done: int, total: int) -> None:
        self.progress.value = done / total
        self.log.push(f"Progress: {done / total:.0%} ({done}/{total})")

    async def _simulated_task(self, duration: int) -> None:
        for i in range(duration):
            await asyncio.sleep(1)
            self._set_progress(i + 1, duration)

    async def _subprocess_task(self, duration: int) -> None:
        """Stream a child process's stdout into the log (ui.log escapes text, unlike raw ui.html)."""
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-u", str(LONG_TASK_SCRIPT), str(duration),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        assert process.stdout is not None
        try:
            async for raw in process.stdout:
                self.log.push(raw.decode(errors="replace").rstrip())
            await process.wait()
            if process.returncode:
                raise RuntimeError(f"process exited with code {process.returncode}")
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()

    async def _run(self, job: Callable[[int], Awaitable[None]], fullscreen: bool = False) -> None:
        if self.task is not None and not self.task.done():
            ui.notify("A task is already running", type="warning")
            return
        self.log.clear()
        self.progress.value = 0
        self.task = asyncio.create_task(job(self._duration()))
        if fullscreen:
            self.overlay.show("Processing...")
        try:
            await asyncio.wait({self.task})  # doesn't propagate cancellation of the task to us
        finally:
            self.overlay.hide()
        if self.task.cancelled():
            self.log.push("Task cancelled")
            ui.notify("Task cancelled", type="warning")
        elif (error := self.task.exception()) is not None:
            self.log.push(f"Task failed: {error}")
            ui.notify(f"Task failed: {error}", type="negative")
        else:
            self.progress.value = 1
            self.log.push("Task completed!")
            ui.notify("Task completed", type="positive")

    def _cancel(self) -> None:
        if self.task is not None and not self.task.done():
            self.task.cancel()

    def build(self) -> None:
        ui.label("Long-Running Task Demo").classes("text-2xl font-bold")
        self.duration_input = ui.number("Duration (seconds)", value=10, min=1, max=60, precision=0)
        self.progress = ui.linear_progress(value=0, show_value=False).classes("w-full")
        self.log = ui.log(max_lines=500).classes("w-full h-72 bg-gray-900 text-green-400")
        self.overlay = FullscreenSpinner(on_cancel=self._cancel)

        with ui.row().classes("gap-2"):
            ui.button("Start Task", on_click=lambda: self._run(self._simulated_task))
            ui.button("Run Subprocess", on_click=lambda: self._run(self._subprocess_task))
            ui.button("Start with Full-Screen Spinner",
                      on_click=lambda: self._run(self._simulated_task, fullscreen=True))
            ui.button("Cancel Task", on_click=self._cancel, color="negative")

        # Don't leave work running for a tab that has been closed.
        ui.context.client.on_delete(self._cancel)
