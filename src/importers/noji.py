from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import TYPE_CHECKING, Any

import requests
from anki.consts import MODEL_CLOZE
from anki.decks import DeckId
from anki.models import NotetypeDict, NotetypeId

if TYPE_CHECKING:
    from aqt.main import AnkiQt

from enum import Enum

from ..config import config
from ..log import logger
from .httpclient import HttpClient
from .importer import CopycatImporter
from .utils import fname_to_link, guess_extension


@dataclass
class NojiDeck:
    id: int
    anki_id: DeckId
    name: str
    card_count: int


class NojiNotetypeKind(Enum):
    BASIC = 0
    REVERSED = 1
    CLOZE = 2

    @classmethod
    def type_for_string(cls, type_str: str) -> NojiNotetypeKind:
        if type_str == "reversed":
            return cls.REVERSED
        elif type_str == "cloze":
            return cls.CLOZE
        return cls.BASIC


@dataclass
class NojiNotetype:
    name: str
    templates: list[tuple[str, str]]
    css: str
    is_cloze: bool = False


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

cloze_template = (
    "{{cloze:Front}}",
    """{{cloze:Front}}<br>
{{Back}}""",
)

cloze_css = """.card {
    font-family: arial;
    font-size: 20px;
    text-align: center;
    color: black;
    background-color: white;
}
.cloze {
    font-weight: bold;
    color: blue;
}
.nightMode .cloze {
    color: lightblue;
}
"""

noji_notetypes = {
    NojiNotetypeKind.BASIC: NojiNotetype("Noji Basic", [basic_template], basic_css),
    NojiNotetypeKind.REVERSED: NojiNotetype(
        "Noji Basic (and reversed card)",
        [basic_template, reversed_template],
        basic_css,
    ),
    NojiNotetypeKind.CLOZE: NojiNotetype(
        "Noji Cloze",
        [cloze_template],
        cloze_css,
        is_cloze=True,
    ),
}


class NojiImporter(CopycatImporter):
    name = "Noji"

    def __init__(self, mw: AnkiQt, token: str):
        super().__init__()
        self.mw = mw
        self.http_client = HttpClient()
        self.token = token

    def _get(self, url: str, *args: Any, **kwrags: Any) -> requests.Response:
        return self.http_client.request("GET", url, *args, **kwrags)

    def _api_get(self, path: str, *args: Any, **kwrags: Any) -> requests.Response:
        return self._get(
            f"https://api-proxy-us.noji.io/api/{path}",
            headers={"Authorization": f"Bearer {self.token}"},
            *args,
            **kwrags,
        )

    def _get_media(self, url: str) -> tuple[str, bytes] | None:
        if not config["download_media"]:
            return None
        try:
            res = self._get(url)
            mime = res.headers.get("content-type", None)
            if not mime:
                return None
            data = res.content
        except Exception:
            self.warnings.append(f"Failed to download media file: {url}")
            return None
        else:
            return mime, data

    def _import_decks(self) -> None:
        res = self._api_get("decks")
        data = res.json()
        decks: dict[int, NojiDeck] = {}
        for deck_dict in data.get("decks", []):
            deck = NojiDeck(
                deck_dict["id"],
                DeckId(1),
                deck_dict["name"],
                deck_dict["totalCardsCount"],
            )
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
        self.notetypes: dict[NojiNotetypeKind, NotetypeDict] = {}
        for kind, noji_notetype in noji_notetypes.items():
            notetype = self.mw.col.models.new(noji_notetype.name)
            notetype["css"] = noji_notetype.css
            if noji_notetype.is_cloze:
                notetype["type"] = MODEL_CLOZE
            for n, (front, back) in enumerate(noji_notetype.templates, start=1):
                template = self.mw.col.models.new_template(f"Card {n}")
                template["qfmt"] = front
                template["afmt"] = back
                self.mw.col.models.add_template(notetype, template)
            for field_name in ("Front", "Back"):
                field = self.mw.col.models.new_field(field_name)
                self.mw.col.models.add_field(notetype, field)
            changes = self.mw.col.models.add_dict(notetype)
            self.notetypes[kind] = self.mw.col.models.get(NotetypeId(changes.id))

    def _process_tts_map(self, side: str, tts_map: dict[str, Any]) -> str:
        tts_list = []
        for tts in tts_map.get(side, []):
            lang_parts = tts["language"].split("-")
            lang_parts[0] = lang_parts[0].lower()
            if len(lang_parts) == 2:
                lang_parts[1] = lang_parts[1].upper()
            lang = "_".join(lang_parts)
            tts_list.append(f"[anki:tts lang={lang}]{tts['text']}[/anki:tts]")

        return "".join(tts_list)

    def _import_cards_for_notes(self, deck: NojiDeck, note_dicts: dict[str, dict], imported_cids: set[str]) -> int:
        if not note_dicts:
            return 0
        count = 0
        res = self._api_get(
            "notes/cards",
            params={
                "deck_id": deck.id,
                "ids": ",".join(note_dicts.keys()),
            },
        )
        card_dicts = res.json()
        for card_dict in card_dicts:
            try:
                cid = card_dict["id"]
                if cid in imported_cids:
                    continue
                imported_cids.add(cid)
                note_dict = note_dicts.get(cid.split("-")[0])
                label = card_dict.get("label", {})
                notetype = self.notetypes[NojiNotetypeKind.type_for_string(label.get("type", ""))]
                note = self.mw.col.new_note(notetype)
                media_urls_map: dict[str, str] = note_dict.get("fieldAttachmentUrls", {})
                media_side_map: dict[str, Any] = note_dict.get("fieldAttachmentsMap", {})
                tts_map: dict[str, Any] = note_dict.get("textToSpeechMap", {})
                media_refs_map = {}
                for id, url in media_urls_map.items():
                    media_info = self._get_media(url)
                    ext = ""
                    data = b""
                    if media_info:
                        mime, data = media_info
                        ext = guess_extension(mime)
                        if not ext:
                            self.warnings.append(f"unrecognized mime for media file {id}: {mime}")
                    if not ext:
                        # Assume PNG if type is not recognized or media download fails or is disabled
                        ext = ".png"
                    filename = f"{id}{ext}"
                    filename = self.mw.col.media.write_data(filename, data)
                    media_refs_map[str(id)] = fname_to_link(filename)

                for i, side in enumerate(("front", "back")):
                    contents = ""
                    media_ids = [t["id"] if isinstance(t, dict) else t for t in media_side_map.get(f"{side}_side", [])]
                    if media_ids:
                        contents += "<br>".join(
                            media_refs_map[str(id)] for id in media_ids if str(id) in media_refs_map
                        )
                    contents += self._process_tts_map(side, tts_map)
                    contents += card_dict["fields"][f"{side}_side"]
                    note.fields[i] = contents
            except Exception as exc:
                logger.warning(
                    "unexpected error while parsing note in deck %s: exc=%s, note=%s",
                    deck.id,
                    str(exc),
                    card_dict,
                )
                raise
            self.mw.col.add_note(note, deck.anki_id)
            count += 1
        return count

    def _import_cards(self) -> int:
        limit = 20
        count = 0
        imported_cids: set[str] = set()
        for deck in self.decks:
            offset = 0
            while offset < deck.card_count:
                res = self._api_get(
                    "notes",
                    params={
                        "deck_id": deck.id,
                        "limit": limit,
                        "offset": offset,
                    },
                )
                data = res.json()
                if not isinstance(data, list):
                    break
                note_dicts = {note["id"]: note for note in data}
                count += self._import_cards_for_notes(deck, note_dicts, imported_cids)
                offset += limit
        return count

    def do_import(self) -> int:
        self._import_decks()
        self._import_notetypes()
        return self._import_cards()
