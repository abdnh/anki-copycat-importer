from typing import Any, Optional

from aqt.qt import *

from ...forms.ankipro import Ui_Form
from .widget import ImporterWidget


class AnkiProWidget(ImporterWidget):
    def setup_ui(self) -> None:
        self.form = Ui_Form()
        self.form.setupUi(self)

    def on_import(self) -> Optional[dict[str, Any]]:
        return {
            "mw": self.importer_dialog.mw,
            "email": self.form.email.text(),
            "password": self.form.password.text(),
        }

    def on_done(self, imported_count: int) -> bool:
        return True
