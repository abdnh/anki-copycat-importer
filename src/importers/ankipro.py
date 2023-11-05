from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Optional

import requests
from anki.decks import DeckId
from anki.models import NotetypeDict, NotetypeId
from aqt.main import AnkiQt

from ..log import logger
from .errors import CopycatImporterError
from .importer import CopycatImporter


@dataclass
class AnkiProDeck:
    id: str
    anki_id: DeckId
    name: str


@dataclass
class AnkiProNotetype:
    name: str
    templates: list[tuple[str, str]]
    css: str


basic_template = (
    "{{Front}}",
    dedent(
        """{{FrontSide}}

<hr id=answer>

{{Back}}"""
    ),
)

reversed_template = (
    "{{Back}}",
    dedent(
        """{{FrontSide}}

<hr id=answer>

{{Front}}"""
    ),
)

basic_css = """.card {
    font-family: arial;
    font-size: 20px;
    text-align: center;
    color: black;
    background-color: white;
}
"""

ankipro_notetypes = [
    AnkiProNotetype("AnkiPro Basic", [basic_template], basic_css),
    AnkiProNotetype(
        "AnkiPro Basic (and reversed card)",
        [basic_template, reversed_template],
        basic_css,
    ),
]


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
        decks: dict[str, AnkiProDeck] = {}
        for deck_dict in data.get("decks", []):
            if not deck_dict.get("clonedFromLibrary", False):
                deck = AnkiProDeck(deck_dict["id"], DeckId(1), deck_dict["name"])
                decks[deck.id] = deck

        def rewrite_deck_names(deck_list: list[dict], parent: str = "") -> None:
            for deck_dict in deck_list:
                if deck_dict["id"] in decks:
                    deck = decks[deck_dict["id"]]
                    if parent:
                        deck.name = f"{parent}::{deck.name}"
                    children = deck_dict.get("children", [])
                    if children:
                        rewrite_deck_names(children, deck.name)

        rewrite_deck_names(data.get("hierarchy", []))
        for deck in decks.values():
            changes = self.mw.col.decks.add_normal_deck_with_name(deck.name)
            deck.anki_id = DeckId(changes.id)

        self.decks = list(decks.values())

    def _import_notetypes(self) -> None:
        self.notetypes: list[NotetypeDict] = []
        for ankipro_notetype in ankipro_notetypes:
            notetype = self.mw.col.models.new(ankipro_notetype.name)
            notetype["css"] = ankipro_notetype.css
            for n, (front, back) in enumerate(ankipro_notetype.templates, start=1):
                template = self.mw.col.models.new_template(f"Card {n}")
                template["qfmt"] = front
                template["afmt"] = back
                self.mw.col.models.add_template(notetype, template)
            for field_name in ("Front", "Back"):
                field = self.mw.col.models.new_field(field_name)
                self.mw.col.models.add_field(notetype, field)
            changes = self.mw.col.models.add_dict(notetype)
            self.notetypes.append(self.mw.col.models.get(NotetypeId(changes.id)))

    def _import_cards(self) -> int:
        count = 0
        for deck in self.decks:
            last_fetched_card_id = None
            while True:
                params = {
                    "deck_id": deck.id,
                    "limit": 20,
                }
                if last_fetched_card_id is not None:
                    params["after"] = last_fetched_card_id
                res = self._get(
                    "notes",
                    params=params,
                )
                note_dicts = res.json()
                if not note_dicts:
                    break
                if not isinstance(note_dicts, list):
                    logger.warning(
                        "got unexpected response while fetching notes of deck %d: %s",
                        deck.id,
                        note_dicts,
                    )
                    break
                for note_dict in note_dicts:
                    label = note_dict.get("label", {})
                    if label.get("type", "") == "reversed":
                        notetype = self.notetypes[1]
                    else:
                        notetype = self.notetypes[0]
                    note = self.mw.col.new_note(notetype)
                    note["Front"] = note_dict["fields"]["front_side"]
                    note["Back"] = note_dict["fields"]["back_side"]
                    self.mw.col.add_note(note, deck.anki_id)
                    count += 1
                last_fetched_card_id = note_dicts[-1]["id"]

        return count

    def do_import(self) -> int:
        self._import_decks()
        self._import_notetypes()
        return self._import_cards()
