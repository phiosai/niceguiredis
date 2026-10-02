from __future__ import annotations

from contextlib import nullcontext
from typing import Any, Awaitable, Callable, Optional

from nicegui import events, ui
from nicegui.elements.upload_files import FileUpload


class FileUploader:
    """Upload widget + server-side processing status.

    Transfer progress is shown by Quasar's uploader itself (real bytes-sent progress); this component
    adds a spinner and result message while ``on_upload`` processes the received file.
    """

    def __init__(
        self,
        label: str = "Upload file",
        on_upload: Optional[Callable[[FileUpload], Awaitable[Any]]] = None,
        accept: Optional[str] = None,
        max_file_size: Optional[int] = None,
    ) -> None:
        self.label = label
        self.on_upload = on_upload
        self.accept = accept
        self.max_file_size = max_file_size
        self.upload: Optional[ui.upload] = None
        self.spinner: Optional[ui.spinner] = None
        self.status_label: Optional[ui.label] = None

    def render(self, parent: Optional[ui.element] = None) -> ui.upload:
        with parent if parent is not None else nullcontext():
            self.upload = ui.upload(
                label=self.label,
                on_upload=self._handle_upload,
                on_rejected=lambda: ui.notify("File rejected (type or size)", type="warning"),
                max_file_size=self.max_file_size,
                auto_upload=True,
            ).classes("w-full")
            if self.accept:
                self.upload.props(f'accept="{self.accept}"')
            with ui.row().classes("items-center gap-2"):
                self.spinner = ui.spinner(size="1.5em")
                self.spinner.set_visibility(False)
                self.status_label = ui.label("").classes("text-sm")
        return self.upload

    def _set_status(self, text: str, color: str = "") -> None:
        if self.status_label is not None:
            self.status_label.text = text
            self.status_label.classes(replace=f"text-sm {color}".strip())

    async def _handle_upload(self, e: events.UploadEventArguments) -> None:
        assert self.spinner is not None
        self.spinner.set_visibility(True)
        self._set_status(f"Processing {e.file.name}...")
        try:
            result = await self.on_upload(e.file) if self.on_upload else None
            self._set_status(str(result) if result is not None else f"{e.file.name} uploaded", "text-positive")
        except Exception as ex:
            self._set_status(f"Upload failed: {ex}", "text-negative")
        finally:
            self.spinner.set_visibility(False)
            if self.upload is not None:
                self.upload.reset()
