from typing import Any, Optional

from aqt.main import AnkiQt
from aqt.qt import Callable, QWidget, qconnect
from aqt.utils import showWarning

from ...config import config
from ...consts import consts
from ...forms.ankipro import Ui_Form
from ..web import WebDialog
from .widget import ImporterWidget


class AnkiProLoginDialog(WebDialog):
    def __init__(self, mw: AnkiQt, parent: QWidget, on_result: Callable[[str], None]):
        super().__init__(mw, parent, "https://noji.io/", "Login to AnkiPro", on_result)

    def get_result(self, on_done: Callable[[str], None]) -> None:
        self.web.page().runJavaScript(
            """
(() => {
    let token = document.cookie.split("; ").find((row) => row.startsWith("AnkiProToken="))?.split("=")[1];
    if(!token) {
          token = localStorage.getItem("AnkiProToken");
    }
    return token;
})();
""",
            on_done,
        )

        return super().get_result(on_done)


class AnkiProWidget(ImporterWidget):
    def setup_ui(self) -> None:
        self.form = Ui_Form()
        self.form.setupUi(self)
        qconnect(self.form.login_button.clicked, self.on_login)
        self._update_login_status(self.token)

    @property
    def token(self) -> Optional[str]:
        return config.importer_options("ankipro").get("token", None)

    def _update_login_status(self, token: str) -> None:
        if token:
            label = "logged in"
            color = "green"
        else:
            label = "not logged in"
            color = "red"
        self.form.login_status.setText(f"Status: <font color='{color}'>{label}</font>")
        self.form.login_instructions.setVisible(not bool(token))
        self.form.token.setText(token)
        if token:
            self.importer_dialog.import_button.setFocus()
        else:
            self.form.login_button.setFocus()

    def on_login(self) -> None:
        dialog = AnkiProLoginDialog(
            self.importer_dialog.mw,
            self.importer_dialog.mw,
            on_result=self._update_login_status,
        )
        dialog.exec()

    def on_import(self) -> Optional[dict[str, Any]]:
        token = self.form.token.text() or self.token
        importer_options = config["importer_options"]
        importer_options["ankipro"]["token"] = token
        config["importer_options"] = importer_options
        if not token:
            showWarning("Not logged in", parent=self, title=consts.name)
            return None
        return {
            "mw": self.importer_dialog.mw,
            "token": token,
        }

    def on_done(self, imported_count: int) -> bool:
        return True
