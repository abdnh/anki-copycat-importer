from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aqt.qt import QWidget

if TYPE_CHECKING:
    from ..importer import ImporterDialog


class ImporterWidget(QWidget):
    def __init__(self, importer_dialog: ImporterDialog):
        super().__init__(importer_dialog)
        self.importer_dialog = importer_dialog
        self.setup_ui()

    def setup_ui(self) -> None:
        pass

    def on_import(self) -> dict[str, Any] | None:
        pass

    def on_done(self, imported_count: int) -> bool:
        pass
