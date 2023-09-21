from pathlib import Path
from typing import Optional

import ankiutils.gui.dialog
from aqt.qt import *
from aqt.utils import getFile, showWarning

from ..appdata import AnkiAppData, get_ankiapp_data_folder
from ..config import config
from ..consts import consts
from ..forms.dialog import Ui_Dialog


class Dialog(ankiutils.gui.dialog.Dialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        on_done: Callable[[Path], None] = None,
    ) -> None:
        super().__init__(__name__, parent)
        self._on_done = on_done

    def setup_ui(self) -> None:
        self.form = Ui_Dialog()
        self.form.setupUi(self)
        super().setup_ui()
        self.setWindowTitle(consts.name)

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
        qconnect(self.form.import_button.clicked, self.on_import)

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
        assert isinstance(file, str)
        if file:
            file = os.path.normpath(file)
            self.form.database_file.setText(file)

    def on_import(self) -> None:
        db_path: Optional[Path] = None
        if self.form.database_file_checkbox.isChecked():
            db_path = Path(self.form.database_file.text())
        else:
            appdata = AnkiAppData(self.form.data_folder.text())
            if appdata.sqlite_dbs:
                db_path = appdata.sqlite_dbs[0]
        if not db_path or not db_path.exists():
            showWarning(
                "Path is empty or doesn't exist", parent=self, title=consts.name
            )
            return

        self.accept()
        self._on_done(db_path)
