from .ankiapp import AnkiAppWidget
from .ankipro import AnkiProWidget
from .widget import ImporterWidget

IMPORTER_WIDGETS: dict[str, type[ImporterWidget]] = {
    "AnkiApp": AnkiAppWidget,
    "AnkiPro": AnkiProWidget,
}
