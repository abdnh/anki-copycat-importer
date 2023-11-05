from typing import Type

from .ankiapp import AnkiAppImporter
from .ankipro import AnkiProImporter
from .importer import CopycatImporter

IMPORTERS: list[Type[CopycatImporter]] = [AnkiAppImporter, AnkiProImporter]
