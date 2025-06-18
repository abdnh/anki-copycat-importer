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
class AnkiProDeck:
    id: int
    anki_id: DeckId
    name: str
    card_count: int


class AnkiProNotetypeKind(Enum):
    BASIC = 0
    REVERSED = 1
    CLOZE = 2

    @classmethod
    def type_for_string(cls, type_str: str) -> AnkiProNotetypeKind:
        if type_str == "reversed":
            return cls.REVERSED
        elif type_str == "cloze":
            return cls.CLOZE
        return cls.BASIC


@dataclass
class AnkiProNotetype:
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

ankipro_notetypes = {
    AnkiProNotetypeKind.BASIC: AnkiProNotetype(
        "AnkiPro Basic", [basic_template], basic_css
    ),
    AnkiProNotetypeKind.REVERSED: AnkiProNotetype(
        "AnkiPro Basic (and reversed card)",
        [basic_template, reversed_template],
        basic_css,
    ),
    AnkiProNotetypeKind.CLOZE: AnkiProNotetype(
        "AnkiPro Cloze",
        [cloze_template],
        cloze_css,
        is_cloze=True,
    ),
}


class AnkiProImporter(CopycatImporter):
    name = "AnkiPro/Noji"

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
        res = self._get(url)
        mime = res.headers.get("content-type", None)
        if not mime:
            return None
        data = res.content

        return mime, data

    def _import_decks(self) -> None:
        res = self._api_get("decks")
        data = res.json()
        decks: dict[int, AnkiProDeck] = {}
        for deck_dict in data.get("decks", []):
            deck = AnkiProDeck(
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
        self.notetypes: dict[AnkiProNotetypeKind, NotetypeDict] = {}
        for kind, ankipro_notetype in ankipro_notetypes.items():
            notetype = self.mw.col.models.new(ankipro_notetype.name)
            notetype["css"] = ankipro_notetype.css
            if ankipro_notetype.is_cloze:
                notetype["type"] = MODEL_CLOZE
            for n, (front, back) in enumerate(ankipro_notetype.templates, start=1):
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
        for tts in tts_map[side]:
            lang_parts = tts["language"].split("-")
            lang_parts[0] = lang_parts[0].lower()
            if len(lang_parts) == 2:
                lang_parts[1] = lang_parts[1].upper()
            lang = "_".join(lang_parts)
            tts_list.append(f"[anki:tts lang={lang}]{tts['text']}[/anki:tts]")
        return "".join(tts_list)

    def _import_cards(self) -> int:
        limit = 20
        count = 0
        imported_cids = set()
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
                note_dicts = res.json()
                if not isinstance(note_dicts, list):
                    break
                note_ids = ",".join([note_dict["id"] for note_dict in note_dicts])
                res = self._api_get(
                    "notes/cards",
                    params={
                        "deck_id": deck.id,
                        "ids": note_ids,
                    },
                )
                note_dicts = res.json()
                for note_dict in note_dicts:
                    try:
                        cid = note_dict["id"]
                        if cid in imported_cids:
                            continue
                        imported_cids.add(cid)
                        label = note_dict.get("label", {})
                        notetype = self.notetypes[
                            AnkiProNotetypeKind.type_for_string(label.get("type", ""))
                        ]
                        note = self.mw.col.new_note(notetype)
                        media_urls_map: dict[str, str] = note_dict.get(
                            "fieldAttachmentUrls", {}
                        )
                        media_side_map: dict[str, Any] = note_dict.get(
                            "fieldAttachmentsMap", {}
                        )
                        tts_map: dict[str, Any] = note_dict.get("textToSpeechMap", {})
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

                        for i, side in enumerate(("front", "back")):
                            contents = ""
                            media_ids = [
                                t["id"] if isinstance(t, dict) else t
                                for t in media_side_map.get(f"{side}_side", [])
                            ]
                            if media_ids:
                                contents += "<br>".join(
                                    media_refs_map[id]
                                    for id in media_ids
                                    if id in media_refs_map
                                )
                            contents += self._process_tts_map(side, tts_map)
                            contents += note_dict["fields"][f"{side}_side"]
                            note.fields[i] = contents
                    except Exception as exc:
                        logger.warning(
                            "unexpected error while parsing note in deck %s: exc=%s, note=%s",
                            deck.id,
                            str(exc),
                            note_dict,
                        )
                        raise exc
                    self.mw.col.add_note(note, deck.anki_id)
                    count += 1
                offset += limit
        return count

    def do_import(self) -> int:
        self._import_decks()
        self._import_notetypes()
        return self._import_cards()
