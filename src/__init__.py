from asyncio import Future
from aqt import mw
from aqt.qt import *
from aqt.utils import getFile, tooltip

from .ankiapp_importer import AnkiAppImporter


def import_from_ankiapp(filename):
    mw.progress.start(
        label="Extracting collection from AnkiApp database...",
        immediate=True,
    )
    mw.progress.set_title("AnkiApp Importer")

    def start_importing():
        importer = AnkiAppImporter(filename)
        importer.import_to_anki(mw)

    def on_done(fut: Future) -> None:
        mw.progress.finish()
        fut.result()
        tooltip("Imported successfully.")
        mw.reset()

    mw.taskman.run_in_background(start_importing, on_done)


action = QAction(mw)
action.setText("Import From AnkiApp")
mw.form.menuTools.addAction(action)
action.triggered.connect(
    lambda: getFile(
        mw,
        "AnkiApp database file to import",
        key="AnkiAppImporter",
        cb=import_from_ankiapp,
    )
)
