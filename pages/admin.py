from __future__ import annotations

import csv
import io

from nicegui import ui
from nicegui.elements.upload_files import FileUpload

from components.collapsible_panel import CollapsiblePanel
from components.file_uploader import FileUploader
from components.loading_spinner import LoadingSpinner
from pages.base import BasePage

COLUMNS = [
    {"name": "id", "label": "ID", "field": "id", "sortable": True},
    {"name": "name", "label": "Name", "field": "name"},
    {"name": "value", "label": "Value", "field": "value"},
    {"name": "created_at", "label": "Created", "field": "created_at"},
]


class AdminPage(BasePage):
    route = "/admin"
    title = "Admin Panel"

    async def _load_data(self) -> None:
        try:
            rows = await self.services.postgres.fetch(
                "SELECT id, name, value, created_at FROM admin_logs ORDER BY id DESC LIMIT 100"
            )
        except Exception as e:
            ui.notify(f"Could not load data: {e}", type="negative")
            return
        for row in rows:
            row["created_at"] = row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        self.table.rows = rows

    async def _create_record(self) -> None:
        name, value = (self.name_input.value or "").strip(), (self.value_input.value or "").strip()
        if not name or not value:
            ui.notify("Name and value are required", type="warning")
            return
        try:
            await self.services.postgres.execute(
                "INSERT INTO admin_logs (name, value) VALUES ($1, $2)", name, value
            )
        except Exception as e:
            ui.notify(f"Insert failed: {e}", type="negative")
            return
        self.name_input.value = self.value_input.value = ""
        ui.notify("Record created", type="positive")
        await self._load_data()

    async def _import_csv(self, file: FileUpload) -> str:
        """Import ``name,value`` rows (header optional) in one transaction."""
        reader = csv.reader(io.StringIO(await file.text()))
        rows = [(r[0].strip(), r[1].strip()) for r in reader if len(r) >= 2 and r[0].strip()]
        if rows and rows[0] == ("name", "value"):
            rows = rows[1:]
        if not rows:
            raise ValueError("no name,value rows found")
        await self.services.postgres.executemany(
            "INSERT INTO admin_logs (name, value) VALUES ($1, $2)", rows
        )
        await self._load_data()
        return f"Imported {len(rows)} row(s) from {file.name}"

    def build(self) -> None:
        ui.label("Admin Panel").classes("text-2xl font-bold")

        create_panel = CollapsiblePanel("Create New Record")
        create_panel.render()
        assert create_panel.content is not None
        with create_panel.content:
            with ui.row().classes("items-end gap-2"):
                self.name_input = ui.input("Name")
                self.value_input = ui.input("Value").on("keydown.enter", self._create_record)
                ui.button("Create", on_click=self._create_record)

        import_panel = CollapsiblePanel("Import CSV (name,value)", default_open=False)
        import_panel.render()
        FileUploader("Drop a .csv file", on_upload=self._import_csv, accept=".csv,text/csv",
                     max_file_size=5_000_000).render(import_panel.content)

        with ui.row().classes("w-full justify-end"):
            ui.button(icon="refresh", on_click=self._load_data).props("flat round")
        spinner = LoadingSpinner(message="Loading data...")
        spinner.show()
        self.table = ui.table(columns=COLUMNS, rows=[], row_key="id").classes("w-full")

        async def initial_load() -> None:
            try:
                await self._load_data()
            finally:
                spinner.hide()

        ui.timer(0, initial_load, once=True)
