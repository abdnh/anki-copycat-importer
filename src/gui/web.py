from __future__ import annotations

from typing import Any, Callable

from aqt.main import AnkiQt
from aqt.qt import (
    QCloseEvent,
    QObject,
    Qt,
    QUrl,
    QVBoxLayout,
    QWebEngineSettings,
    QWebEngineUrlRequestInterceptor,
    QWidget,
    qconnect,
)
from aqt.webview import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineUrlRequestInfo,
    QWebEngineView,
)

from ..consts import USER_AGENT, consts
from .dialog import Dialog


class RequestInterceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        info.setHttpHeader(
            b"User-Agent",
            USER_AGENT.encode(),
        )


class WebProfile(QWebEngineProfile):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__("copycat_importer", parent)
        self.setUrlRequestInterceptor(RequestInterceptor(self))


web_profile = WebProfile()


class WebPage(QWebEnginePage):
    def __init__(self, mw: AnkiQt, parent: QWidget) -> None:
        super().__init__(web_profile, parent)
        self.mw = mw
        self._parent = parent


class Webview(QWebEngineView):
    def __init__(self, mw: AnkiQt, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.mw = mw
        self._parent = parent
        self._page = WebPage(mw, self)
        qconnect(self._page.windowCloseRequested, self.on_close_requested)
        self.setPage(self._page)

    def on_close_requested(self) -> None:
        self._parent.close()


class WebDialog(Dialog):
    def __init__(
        self,
        mw: AnkiQt,
        parent: QWidget,
        url: str,
        title: str,
        on_result: Callable[[Any], None],
    ):
        self.mw = mw
        self.url = url
        self.title = title
        self._on_result = on_result
        super().__init__(parent, Qt.WindowType.Window)

    def setup_ui(self) -> None:
        self.setWindowTitle(f"{consts.name} - {self.title}")
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)
        vbox = QVBoxLayout()
        self.web = Webview(self.mw, self)
        vbox.addWidget(self.web)
        self.web.settings().setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent,
            True,
        )
        self.web.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            True,
        )
        self.web.setUrl(QUrl(self.url))
        self.setLayout(vbox)
        super().setup_ui()

    def get_result(self, on_done: Callable[[Any], None]) -> None:
        on_done("")

    def closeEvent(self, event: QCloseEvent) -> None:
        base_close = super().closeEvent

        def on_result(result: Any) -> None:
            base_close(event)
            self._on_result(result)

        self.get_result(on_result)
