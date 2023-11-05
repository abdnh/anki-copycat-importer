from pathlib import Path
from textwrap import dedent
from typing import Any, Optional

from aqt import mw
from aqt.qt import *
from aqt.utils import getFile, showWarning

from ...appdata import get_ankiapp_data_folder
from ...config import config
from ...consts import consts
from ...forms.ankiapp import Ui_Form
from ...importers.ankiapp import ImportedPathType
from .widget import ImporterWidget


class AnkiAppWidget(ImporterWidget):
    def setup_ui(self) -> None:
        self.form = Ui_Form()
        self.form.setupUi(self)
        qconnect(self.form.data_folder_checkbox.toggled, self.on_data_folder_toggled)
        qconnect(
            self.form.database_file_checkbox.toggled, self.on_database_file_toggled
        )
        self.form.remote_media.setChecked(config["remote_media"])
        qconnect(self.form.remote_media.toggled, self.on_remote_media_toggled)
        ankiapp_data_folder = get_ankiapp_data_folder()
        if ankiapp_data_folder:
            self.form.data_folder.setText(ankiapp_data_folder)
        qconnect(self.form.choose_data_folder.clicked, self.on_choose_data_folder)
        qconnect(self.form.choose_database_file.clicked, self.on_choose_database_file)

    def on_data_folder_toggled(self, checked: bool) -> None:
        if checked:
            self.form.data_folder.setEnabled(True)
            self.form.choose_data_folder.setEnabled(True)
            self.form.database_file.setEnabled(False)
            self.form.choose_database_file.setEnabled(False)

    def on_database_file_toggled(self, checked: bool) -> None:
        if checked:
            self.form.database_file.setEnabled(True)
            self.form.choose_database_file.setEnabled(True)
            self.form.data_folder.setEnabled(False)
            self.form.choose_data_folder.setEnabled(False)

    def on_remote_media_toggled(self, checked: bool) -> None:
        config["remote_media"] = checked

    def on_choose_data_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose AnkiApp data folder")
        if folder:
            self.form.data_folder.setText(folder)

    def on_choose_database_file(self) -> None:
        file = getFile(self, consts.name, cb=None, filter="*")
        if file:
            assert isinstance(file, str)
            file = os.path.normpath(file)
            self.form.database_file.setText(file)

    def on_import(self) -> Optional[dict[str, Any]]:
        path: Optional[Path] = None
        path_type: Optional[ImportedPathType] = None
        if self.form.database_file_checkbox.isChecked():
            path = Path(self.form.database_file.text())
            path_type = ImportedPathType.DB_PATH
        else:
            path = Path(self.form.data_folder.text())
            path_type = ImportedPathType.DATA_DIR
        if not path or not path.exists():
            showWarning(
                "Path is empty or doesn't exist", parent=self, title=consts.name
            )
            return None

        return {"mw": self.importer_dialog.mw, "path": path, "path_type": path_type}

    def on_done(self, imported_count: int) -> bool:
        if not imported_count:
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
            return False
        return True
