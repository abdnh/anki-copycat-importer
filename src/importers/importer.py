from abc import ABC, abstractmethod
from typing import Any


class CopycatImporter(ABC):
    name: str

    def __init__(self, *args: Any, **kwargs: Any):
        self.warnings: list[str] = []

    @abstractmethod
    def do_import(self) -> int:
        return 0
