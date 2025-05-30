import functools
import os
import sys
from typing import Type

from aqt import mw
from aqt.qt import QAction, QMenu, qconnect

sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))

from .errors import setup_error_handler
from .gui.dialog import ImporterDialog
from .importers import IMPORTERS, CopycatImporter


def on_action(importer_class: Type[CopycatImporter]) -> None:
    dialog = ImporterDialog(mw, importer_class)
    dialog.open()


menu = QMenu("Copycat Importer", mw)
for importer_class in IMPORTERS:
    action = QAction(f"Import from {importer_class.name}", menu)
    qconnect(
        action.triggered, functools.partial(on_action, importer_class=importer_class)
    )
    menu.addAction(action)


def init() -> None:
    setup_error_handler()
    mw.form.menuTools.addMenu(menu)
