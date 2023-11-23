from typing import Any, Optional

from aqt.main import AnkiQt
from aqt.qt import *
from aqt.utils import showWarning
from aqt.webview import QWebEnginePage, QWebEngineProfile

from ...config import config
from ...consts import consts
from ...forms.ankipro import Ui_Form
from .widget import ImporterWidget

web_profile = QWebEngineProfile("copycat_importer")


class AnkiProWebPage(QWebEnginePage):
    def __init__(self, mw: AnkiQt, parent: QWidget) -> None:
        super().__init__(web_profile, parent)
        self.mw = mw
        self._parent = parent
        # FIXME: Qt5
        if qtmajor >= 6:
            qconnect(self.newWindowRequested, self.on_new_window_requested)

    def on_new_window_requested(self, request: "QWebEngineNewWindowRequest") -> None:
        dialog = AnkiProLoginDialog(self.mw, self._parent, lambda: None)
        request.openIn(dialog.web.page())
        dialog.open()


class AnkiProWebview(QWebEngineView):
    def __init__(self, mw: AnkiQt, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.mw = mw
        self._parent = parent
        self._page = AnkiProWebPage(mw, self)
        qconnect(self._page.windowCloseRequested, self.on_close_requested)
        self.setPage(self._page)

    def on_close_requested(self) -> None:
        self._parent.close()


class AnkiProLoginDialog(QDialog):
    URL = "https://ankipro.net/"

    def __init__(
        self,
        mw: AnkiQt,
        parent: QWidget,
        on_finished: Callable[[], None],
    ):
        super().__init__(parent, Qt.WindowType.Window)
        self.mw = mw
        self.on_finished = on_finished
        self.setWindowTitle(f"{consts.name} - AnkiPro Login")
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        vbox = QVBoxLayout()
        self.web = AnkiProWebview(self.mw, self)
        vbox.addWidget(self.web)
        self.web.settings().setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent,
            True,
        )
        self.web.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            True,
        )
        self.web.setUrl(QUrl(self.URL))
        self.setLayout(vbox)

    def closeEvent(self, event: QCloseEvent) -> None:
        base_close = super().closeEvent

        def on_login(token: str) -> None:
            if token:
                importer_options = config["importer_options"]
                importer_options["ankipro"]["token"] = token
                config["importer_options"] = importer_options
            base_close(event)
            self.on_finished()

        self.web.page().runJavaScript('localStorage.getItem("AnkiProToken");', on_login)


class AnkiProWidget(ImporterWidget):
    def setup_ui(self) -> None:
        self.form = Ui_Form()
        self.form.setupUi(self)
        qconnect(self.form.login_button.clicked, self.on_login)
        self._update_login_status()

    @property
    def token(self) -> Optional[str]:
        return config.importer_options("ankipro").get("token", None)

    def _update_login_status(self) -> None:
        if self.token:
            label = "logged in"
            color = "green"
        else:
            label = "not logged in"
            color = "red"
        self.form.login_status.setText(f"Status: <font color='{color}'>{label}</font>")
        self.form.login_instructions.setVisible(not bool(self.token))
        if self.token:
            self.importer_dialog.import_button.setFocus()
        else:
            self.form.login_button.setFocus()

    def on_login(self) -> None:
        dialog = AnkiProLoginDialog(
            self.importer_dialog.mw,
            self.importer_dialog.mw,
            on_finished=self._update_login_status,
        )
        dialog.exec()

    def on_import(self) -> Optional[dict[str, Any]]:
        if not self.token:
            showWarning("Not logged in", parent=self, title=consts.name)
            return None
        return {
            "mw": self.importer_dialog.mw,
            "token": self.token,
        }

    def on_done(self, imported_count: int) -> bool:
        return True
