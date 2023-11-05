from typing import Type

from aqt.qt import QWidget

from .ankiapp import AnkiAppWidget
from .ankipro import AnkiProWidget
from .widget import ImporterWidget

IMPORTER_WIDGETS: dict[str, Type[ImporterWidget]] = {
    "AnkiApp": AnkiAppWidget,
    "AnkiPro": AnkiProWidget,
}
