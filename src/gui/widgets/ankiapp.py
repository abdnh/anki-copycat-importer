from typing import Any, Callable, Optional

from aqt.main import AnkiQt
from aqt.qt import QWidget, qconnect
from aqt.utils import showWarning

from ...config import config
from ...consts import consts
from ...forms.ankiapp import Ui_Form
from ..web import WebDialog
from .widget import ImporterWidget


class AnkiAppLoginDialog(WebDialog):
    def __init__(self, mw: AnkiQt, parent: QWidget, on_result: Callable[[Any], None]):
        super().__init__(
            mw, parent, "https://web.ankiapp.com/", "Login to AnkiApp", on_result
        )

    def get_result(self, on_done: Callable[[Any], None]) -> None:
        self.web.page().runJavaScript(
            """
(() => {
    return {
        client_token: localStorage.getItem("AnkiApp.device.token_v2"),
        client_id: localStorage.getItem("AnkiApp.device.id"),
        client_version: localStorage.getItem("AnkiApp.version"),
    };
})();
""",
            on_done,
        )


class AnkiAppWidget(ImporterWidget):
    def setup_ui(self) -> None:
        self.form = Ui_Form()
        self.form.setupUi(self)
        qconnect(self.form.login_button.clicked, self.on_login)
        self._update_login_status(self.login_data)

    @property
    def login_data(self) -> dict[str, str]:
        return config.importer_options("ankiapp")

    def _is_logged_in(self, login_data: dict[str, str]) -> bool:
        return bool(
            login_data.get("client_id", None) and login_data.get("client_token", None)
        )

    def _update_login_status(self, login_data: dict[str, str]) -> None:
        logged_in = self._is_logged_in(login_data)
        if logged_in:
            label = "logged in"
            color = "green"
        else:
            label = "not logged in"
            color = "red"
        self.form.login_status.setText(f"Status: <font color='{color}'>{label}</font>")
        self.form.login_instructions.setVisible(not logged_in)
        if logged_in:
            self.importer_dialog.import_button.setFocus()
        else:
            self.form.login_button.setFocus()

    def _on_login_data(self, login_data: dict[str, str]) -> None:
        importer_options = config["importer_options"]
        importer_options["ankiapp"]["client_id"] = login_data["client_id"]
        importer_options["ankiapp"]["client_token"] = login_data["client_token"]
        importer_options["ankiapp"]["client_version"] = login_data["client_version"]
        config["importer_options"] = importer_options
        self._update_login_status(login_data)

    def on_login(self) -> None:
        dialog = AnkiAppLoginDialog(
            self.importer_dialog.mw,
            self.importer_dialog.mw,
            on_result=self._on_login_data,
        )
        dialog.exec()

    def on_import(self) -> Optional[dict[str, Any]]:
        if not self._is_logged_in(self.login_data):
            showWarning("Not logged in", parent=self, title=consts.name)
            return None
        return {
            "mw": self.importer_dialog.mw,
            "client_id": self.login_data["client_id"],
            "client_token": self.login_data["client_token"],
            "client_version": self.login_data["client_version"],
        }

    def on_done(self, imported_count: int) -> bool:
        return True
