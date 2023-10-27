from typing import Type

from .ankiapp import AnkiAppImporter
from .importer import CopycatImporter

IMPORTERS: list[Type[CopycatImporter]] = [AnkiAppImporter]
