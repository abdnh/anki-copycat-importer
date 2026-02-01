from .algoapp import AlgoAppImporter
from .importer import CopycatImporter
from .noji import NojiImporter

IMPORTERS: list[type[CopycatImporter]] = [AlgoAppImporter, NojiImporter]
