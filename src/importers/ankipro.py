from dataclasses import dataclass
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Optional

import requests
from anki.decks import DeckId
from anki.models import NotetypeDict, NotetypeId

if TYPE_CHECKING:
    from aqt.main import AnkiQt

from ..config import config
from ..log import logger
from .httpclient import HttpClient
from .importer import CopycatImporter
from .utils import fname_to_link, guess_extension


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

    def __init__(self, mw: "AnkiQt", token: str):
        super().__init__()
        self.mw = mw
        self.http_client = HttpClient()
        self.token = token

    def _get(self, url: str, *args: Any, **kwrags: Any) -> requests.Response:
        return self.http_client.request("GET", url, *args, **kwrags)

    def _api_get(self, path: str, *args: Any, **kwrags: Any) -> requests.Response:
        return self._get(
            f"https://api.ankipro.net/api/{path}",
            headers={"Authorization": f"Bearer {self.token}"},
            *args,
            **kwrags,
        )

    def _get_media(self, url: str) -> Optional[tuple[str, bytes]]:
        if not config["download_media"]:
            return None
        res = self._get(url)
        mime = res.headers.get("content-type", None)
        if not mime:
            return None
        data = res.content

        return mime, data

    def _import_decks(self) -> None:
        res = self._api_get("decks")
        data = res.json()
        decks: dict[str, AnkiProDeck] = {}
        for deck_dict in data.get("decks", []):
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

    # pylint: disable=too-many-locals,too-many-branches
    def _import_cards(self) -> int:
        count = 0
        for deck in self.decks:
            offset = 0
            while True:
                params = {
                    "deck_id": deck.id,
                    "limit": 20,
                    "offset": offset,
                }
                res = self._api_get(
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
                    media_urls_map: dict[str, str] = note_dict.get(
                        "fieldAttachmentUrls", {}
                    )
                    media_side_map: dict[str, Any] = note_dict.get(
                        "fieldAttachmentsMap", {}
                    )
                    media_refs_map = {}
                    for id, url in media_urls_map.items():
                        media_info = self._get_media(url)
                        if not media_info:
                            continue
                        mime, data = media_info
                        ext = guess_extension(mime)
                        if not ext:
                            self.warnings.append(
                                f"unrecognized mime for media file {id}: {mime}"
                            )
                        else:
                            filename = f"{id}{ext}"
                            filename = self.mw.col.media.write_data(filename, data)
                            media_refs_map[int(id)] = fname_to_link(filename)

                    for i, side in enumerate(("front_side", "back_side")):
                        contents = ""
                        media_ids = [
                            t["id"] if isinstance(t, dict) else t
                            for t in media_side_map.get(side, [])
                        ]
                        if media_ids:
                            contents += "<br>".join(
                                media_refs_map[id]
                                for id in media_ids
                                if id in media_refs_map
                            )
                        contents += note_dict["fields"][side]
                        note.fields[i] = contents
                    self.mw.col.add_note(note, deck.anki_id)
                    count += 1
                    offset += 1

        return count

    def do_import(self) -> int:
        self._import_decks()
        self._import_notetypes()
        return self._import_cards()
