from typing import Any, Dict

from .ankiutils.config import Config as BaseConfig


class Config(BaseConfig):
    def importer_options(self, name: str) -> Dict[str, Any]:
        return self["importer_options"].get(name, {})


config = Config(__name__)
