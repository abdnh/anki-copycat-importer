from .ankiapp import AnkiAppImporter
from .ankipro import AnkiProImporter
from .importer import CopycatImporter

IMPORTERS: list[type[CopycatImporter]] = [AnkiAppImporter, AnkiProImporter]
