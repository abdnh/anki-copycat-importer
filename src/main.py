import os
import sys
from concurrent.futures import Future
from pathlib import Path
from textwrap import dedent
from typing import Optional

from aqt import mw
from aqt.qt import QAction, qconnect
from aqt.utils import showText, showWarning, tooltip

sys.path.append(os.path.join(os.path.dirname(__file__), "vendor"))

from .ankiapp_importer import (
    AnkiAppImporter,
    AnkiAppImporterCanceledException,
    AnkiAppImporterException,
    ImportedPathType,
)
from .consts import consts
from .gui.dialog import Dialog


def import_from_ankiapp(path: Path, path_type: ImportedPathType) -> None:
    mw.progress.start(
        label="Extracting collection from AnkiApp database...",
        immediate=True,
    )
    mw.progress.set_title(consts.name)

    def start_importing() -> Optional[tuple[int, set[str]]]:
        importer = AnkiAppImporter(mw, path, path_type)
        return importer.import_to_anki(), importer.warnings

    def on_done(fut: Future) -> None:
        mw.progress.finish()
        try:
            count, warnings = fut.result()
            if not count:
                showWarning(
                    dedent(
                        """\
                    No cards were found in your AnkiApp database.
                    Before using this add-on, please make sure you've downloaded the decks on your AnkiApp account by clicking
                    on the Download button shown when you select a deck in AnkiApp.
                    """
                    ),
                    parent=mw,
                    title=consts.name,
                    textFormat="rich",
                )
                return
            if count == 1:
                tooltip(f"Imported {count} card.")
            else:
                tooltip(f"Imported {count} cards.")
            if warnings:
                showText(
                    "The following issues were found:\n" + "\n".join(warnings),
                    title=consts.name,
                )
            mw.reset()
        except AnkiAppImporterCanceledException:
            tooltip("Canceled")
        except AnkiAppImporterException as exc:
            showWarning(str(exc), parent=mw, title=consts.name)

    mw.taskman.run_in_background(start_importing, on_done)


action = QAction(mw)
action.setText("Import From AnkiApp")
mw.form.menuTools.addAction(action)


def on_action() -> None:
    dialog = Dialog(mw, on_done=import_from_ankiapp)
    dialog.open()


qconnect(
    action.triggered,
    on_action,
)
