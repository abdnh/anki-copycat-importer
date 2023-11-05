from dataclasses import dataclass
from typing import Any, Optional

import requests
from aqt.main import AnkiQt

from .errors import CopycatImporterError
from .importer import CopycatImporter


@dataclass
class Deck:
    id: str
    name: str


# pylint: disable=too-few-public-methods
class AnkiProImporter(CopycatImporter):
    name = "AnkiPro"
    ENDPOINT = "https://api.ankipro.net/api"
    TIMEOUT = 60

    def __init__(self, mw: AnkiQt, email: str, password: str):
        super().__init__()
        self.mw = mw
        self.token = self._login(email, password)

    def _login(self, email: str, password: str) -> Optional[str]:
        try:
            res = requests.post(
                f"{self.ENDPOINT}/authentication/login_with_provider",
                data={"email": email, "password": password, "provider": "email"},
                timeout=self.TIMEOUT,
            )
            res.raise_for_status()
            j = res.json()
            if isinstance(j, dict):
                return j.get("token")
            return None
        except requests.HTTPError as exc:
            raise CopycatImporterError(f"Failed to log in: {str(exc)}") from exc

    def _get(self, path: str, *args: Any, **kwrags: Any) -> requests.Response:
        url = f"{self.ENDPOINT}/{path}"
        try:
            return requests.get(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=self.TIMEOUT,
                *args,
                **kwrags,
            )
        except requests.HTTPError as exc:
            raise CopycatImporterError(f"Request to {url} failed: {str(exc)}") from exc

    def _import_decks(self) -> None:
        res = self._get("decks")
        data = res.json()
        decks: dict[str, Deck] = {}
        for deck_dict in data.get("decks", []):
            deck = Deck(deck_dict["id"], deck_dict["name"])
            decks[deck.id] = deck

        def rewrite_deck_names(deck_list: list[dict], parent: str = "") -> None:
            for deck_dict in deck_list:
                deck = decks[deck_dict["id"]]
                if parent:
                    deck.name = f"{parent}::{deck.name}"
                children = deck_dict.get("children", [])
                if children:
                    rewrite_deck_names(children, deck.name)

        rewrite_deck_names(data.get("hierarchy", []))
        for deck in decks.values():
            self.mw.col.decks.add_normal_deck_with_name(deck.name)

    def do_import(self) -> int:
        self._import_decks()

        return 0
