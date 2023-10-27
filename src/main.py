import functools
import os
import sys
from typing import Type

from aqt import mw
from aqt.qt import QAction, QMenu, qconnect

sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))

from .consts import consts
from .gui.dialog import ImporterDialog
from .importers import IMPORTERS, CopycatImporter


def on_action(importer_class: Type[CopycatImporter]) -> None:
    dialog = ImporterDialog(mw, importer_class)
    dialog.open()


menu = QMenu(consts.name, mw)
for importer_class in IMPORTERS:
    action = QAction(f"Import from {importer_class.name}", menu)
    qconnect(
        action.triggered, functools.partial(on_action, importer_class=importer_class)
    )
    menu.addAction(action)

mw.form.menuTools.addMenu(menu)
