from concurrent.futures import Future
from typing import Set, Tuple

import aqt
from aqt.gui_hooks import main_window_did_init
from aqt.main import AnkiQt
from aqt.qt import *
from aqt.utils import getFile, showText, showWarning, tooltip

from .ankiapp_importer import AnkiAppImporter


def import_from_ankiapp(mw: AnkiQt, filename: str) -> None:
    mw.progress.start(
        label="Extracting collection from AnkiApp database...",
        immediate=True,
    )
    mw.progress.set_title("AnkiApp Importer")

    def start_importing() -> Tuple[int, Set[str]]:
        importer = AnkiAppImporter(mw, filename)
        return importer.import_to_anki(), importer.warnings

    def on_done(fut: Future) -> None:
        mw.progress.finish()
        count, warnings = fut.result()
        if count:
            tooltip(f"Successfully imported {count} card(s).")
        else:
            showWarning(
                """\
No cards were found in your AnkiApp database. \
Before using this add-on, please make sure you've downloaded the decks on your AnkiApp account by clicking \
on the Download button shown when you select a deck in AnkiApp.
            """,
                parent=mw,
                title="AnkiApp Importer",
            )
        if warnings:
            showText(
                "The following issues were found:\n" + "\n".join(warnings),
                title="AnkiApp Importer",
            )
        mw.reset()

    mw.taskman.run_in_background(start_importing, on_done)


def on_mw_init() -> None:
    if aqt.mw is not None:
        mw: AnkiQt = aqt.mw
        action = QAction(mw)
        action.setText("Import From AnkiApp")
        mw.form.menuTools.addAction(action)
        qconnect(
            action.triggered,
            lambda: getFile(
                mw,
                "AnkiApp database file to import",
                key="AnkiAppImporter",
                cb=lambda f: import_from_ankiapp(mw, f),
                filter="*",
            ),
        )


main_window_did_init.append(on_mw_init)
