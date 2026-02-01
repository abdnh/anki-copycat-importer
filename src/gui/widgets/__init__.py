from .algoapp import AlgoAppWidget
from .noji import NojiWidget
from .widget import ImporterWidget

IMPORTER_WIDGETS: dict[str, type[ImporterWidget]] = {
    "AlgoApp": AlgoAppWidget,
    "Noji": NojiWidget,
}
