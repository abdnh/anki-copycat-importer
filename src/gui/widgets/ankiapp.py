from pathlib import Path
from textwrap import dedent
from typing import Any, List, Optional

from aqt import mw
from aqt.qt import *
from aqt.utils import getFile, showWarning

from ...appdata import get_ankiapp_data_folder
from ...config import config
from ...consts import consts
from ...forms.ankiapp import Ui_Form
from ...importers.ankiapp import ImportedPathInfo, ImportedPathType
from .widget import ImporterWidget


class AnkiAppWidget(ImporterWidget):
    def setup_ui(self) -> None:
        self.paths: List[ImportedPathInfo] = []
        self.form = Ui_Form()
        self.form.setupUi(self)
        qconnect(self.form.data_folder_checkbox.toggled, self.on_data_folder_toggled)
        qconnect(
            self.form.database_file_checkbox.toggled, self.on_database_file_toggled
        )
        qconnect(self.form.xml_zip_checkbox.toggled, self.on_xml_zip_toggled)
        self.form.remote_media.setChecked(config["remote_media"])
        qconnect(self.form.remote_media.toggled, self.on_remote_media_toggled)
        ankiapp_data_folder = get_ankiapp_data_folder()
        if ankiapp_data_folder:
            self.form.data_folder.setText(ankiapp_data_folder)
            self.paths.append(
                ImportedPathInfo(Path(ankiapp_data_folder), ImportedPathType.DATA_DIR)
            )
        qconnect(self.form.choose_data_folder.clicked, self.on_choose_data_folder)
        qconnect(self.form.choose_database_file.clicked, self.on_choose_database_file)
        qconnect(self.form.choose_xml_zip.clicked, self.on_choose_xml_zip)

    def on_data_folder_toggled(self, checked: bool) -> None:
        if checked:
            self.form.data_folder.setEnabled(True)
            self.form.choose_data_folder.setEnabled(True)
            self.form.database_file.setEnabled(False)
            self.form.choose_database_file.setEnabled(False)
            self.form.xml_zip.setEnabled(False)
            self.form.choose_xml_zip.setEnabled(False)

    def on_database_file_toggled(self, checked: bool) -> None:
        if checked:
            self.form.database_file.setEnabled(True)
            self.form.choose_database_file.setEnabled(True)
            self.form.data_folder.setEnabled(False)
            self.form.choose_data_folder.setEnabled(False)
            self.form.xml_zip.setEnabled(False)
            self.form.choose_xml_zip.setEnabled(False)

    def on_xml_zip_toggled(self, checked: bool) -> None:
        if checked:
            self.form.xml_zip.setEnabled(True)
            self.form.choose_xml_zip.setEnabled(True)
            self.form.database_file.setEnabled(False)
            self.form.choose_database_file.setEnabled(False)
            self.form.data_folder.setEnabled(False)
            self.form.choose_data_folder.setEnabled(False)

    def on_remote_media_toggled(self, checked: bool) -> None:
        config["remote_media"] = checked

    def on_choose_data_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose AnkiApp data folder")
        if folder:
            self.paths = [ImportedPathInfo(Path(folder), ImportedPathType.DATA_DIR)]
            self.form.data_folder.setText(folder)

    def on_choose_database_file(self) -> None:
        files = getFile(self, consts.name, cb=None, filter="*", multi=True)
        if files:
            files = list(files)
            self.paths = [
                ImportedPathInfo(Path(os.path.normpath(file)), ImportedPathType.DB_PATH)
                for file in files
            ]
            self.form.database_file.setText(",".join(files))

    def on_choose_xml_zip(self) -> None:
        files = getFile(self, consts.name, cb=None, filter="*.zip", multi=True)
        if files:
            files = list(files)
            self.paths = [
                ImportedPathInfo(Path(os.path.normpath(file)), ImportedPathType.XML_ZIP)
                for file in files
            ]
            self.form.xml_zip.setText(",".join(files))

    def on_import(self) -> Optional[dict[str, Any]]:
        if all(not info.path or not info.path.exists() for info in self.paths):
            showWarning(
                "Paths are empty or don't exist", parent=self, title=consts.name
            )
            return None

        return {"mw": self.importer_dialog.mw, "paths": self.paths}

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
