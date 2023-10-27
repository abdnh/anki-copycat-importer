from typing import TYPE_CHECKING, Any, Optional

from aqt.qt import QWidget

if TYPE_CHECKING:
    from ..dialog import ImporterDialog


class ImporterWidget(QWidget):
    def __init__(self, importer_dialog: "ImporterDialog"):
        super().__init__(importer_dialog)
        self.importer_dialog = importer_dialog
        self.setup_ui()

    def setup_ui(self) -> None:
        pass

    def on_import(self) -> Optional[dict[str, Any]]:
        pass

    def on_done(self, imported_count: int) -> bool:
        pass
