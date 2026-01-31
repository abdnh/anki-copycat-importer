import functools

from aqt import mw
from aqt.qt import QAction, QMenu, qconnect

from .consts import consts
from .errors import upload_logs_and_notify_user
from .gui.help import HelpDialog
from .gui.importer import ImporterDialog
from .importers import IMPORTERS, CopycatImporter


def on_action(importer_class: type[CopycatImporter]) -> None:
    dialog = ImporterDialog(mw, importer_class)
    dialog.open()


def on_help() -> None:
    HelpDialog().show()


def on_logs() -> None:
    upload_logs_and_notify_user(mw)


def add_menu() -> None:
    menu = QMenu(consts.name, mw)
    for importer_class in IMPORTERS:
        action = QAction(f"Import from {importer_class.name}", menu)
        qconnect(action.triggered, functools.partial(on_action, importer_class=importer_class))
        menu.addAction(action)
    menu.addAction("Upload logs", on_logs)
    menu.addAction("Help", on_help)
    mw.form.menuTools.addMenu(menu)
