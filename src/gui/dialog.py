from concurrent.futures import Future
from typing import Optional, Type

import ankiutils.gui.dialog
from aqt.main import AnkiQt
from aqt.qt import *
from aqt.utils import showText, showWarning, tooltip

from ..consts import consts
from ..importers.errors import CopycatImporterCanceled, CopycatImporterError
from ..importers.importer import CopycatImporter
from .widgets import IMPORTER_WIDGETS


class ImporterDialog(ankiutils.gui.dialog.Dialog):
    def __init__(
        self,
        mw: AnkiQt,
        importer_class: Type[CopycatImporter],
    ) -> None:
        self.mw = mw
        self.importer_class = importer_class
        super().__init__(__name__, mw)

    def setup_ui(self) -> None:
        self.setWindowTitle(f"{consts.name} - {self.importer_class.name}")
        import_button = self.import_button = QPushButton("Import", self)
        qconnect(import_button.clicked, self.on_import)
        layout = QFormLayout(self)
        self.importer_widget = IMPORTER_WIDGETS[self.importer_class.name](self)
        layout.addRow(self.importer_widget)
        layout.addRow(import_button)
        super().setup_ui()

    def on_import(self) -> None:
        options = self.importer_widget.on_import()
        if options is None:
            return
        self.accept()

        self.mw.progress.start(
            label="Importing...",
            immediate=True,
        )
        self.mw.progress.set_title(consts.name)

        def start_importing() -> Optional[tuple[int, list[str]]]:
            importer = self.importer_class(**options)
            return importer.do_import(), importer.warnings

        def on_done(fut: Future) -> None:
            self.mw.progress.finish()
            try:
                count, warnings = fut.result()
                if self.importer_widget.on_done(count):
                    if count == 1:
                        tooltip(f"Imported {count} card.", parent=self.mw)
                    else:
                        tooltip(f"Imported {count} cards.", parent=self.mw)
                    if warnings:
                        showText(
                            "The following issues were found:\n" + "\n".join(warnings),
                            title=consts.name,
                            parent=self.mw,
                        )
                    self.mw.reset()
            except CopycatImporterCanceled:
                tooltip("Canceled")
            except CopycatImporterError as exc:
                showWarning(str(exc), parent=self.mw, title=consts.name)

        self.mw.taskman.run_in_background(start_importing, on_done)
