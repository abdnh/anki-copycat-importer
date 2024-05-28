from __future__ import annotations

import dataclasses
import os
import re
import time
from collections.abc import Iterable, Iterator, MutableSet
from re import Match
from textwrap import dedent
from typing import TYPE_CHECKING, Any, cast

import requests

if TYPE_CHECKING:
    from anki.decks import DeckId
    from anki.models import NotetypeId
    from aqt.main import AnkiQt

from ..log import logger
from .errors import CopycatImporterCanceled
from .httpclient import HttpClient
from .importer import CopycatImporter
from .utils import fname_to_link, guess_extension

INVALID_FIELD_CHARS_RE = re.compile('[:"{}]')


# Must match fix_name in fields.rs: https://github.com/ankitects/anki/blob/404a6c5d4a5fd908a20d8cbdb003c1204e10c0ce/rslib/src/notetype/fields.rs#L55
def fix_field_name(text: str) -> str:
    text = text.strip()
    text = text.lstrip("#/^")
    return INVALID_FIELD_CHARS_RE.sub("", text)


def field_list_to_refs(flds: list[str]) -> str:
    return "<br>".join("{{%s}}" % f for f in flds)


class FieldSet(MutableSet):
    """A set to hold field names and transform fields differing only in case such that they are unique."""

    def __init__(self, iterable: Iterable | None = None) -> None:
        self.map: dict[str, str] = {}
        super().__init__()
        if iterable:
            for el in iterable:
                self.add(el)

    def add(self, key: str) -> None:
        value = key if key not in self else f"{key}+"
        self.map[key] = fix_field_name(value)

    def discard(self, value: str) -> None:
        if value in self.map:
            del self.map[value]

    def get(self, key: str) -> str | None:
        """Return `key` as stored in the set or `None` if not found."""
        return self.map.get(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.map.values())

    def __len__(self) -> int:
        return len(self.map)

    def __contains__(self, field: Any) -> bool:
        for key in self.map:
            if key.lower() == field.lower():
                return True
        return False

    def __repr__(self) -> str:
        return repr(list(self.map.values()))


# pylint: disable=too-many-arguments
class AnkiAppNoteType:
    def __init__(
        self,
        name: str,
        fields: FieldSet,
        style: str,
        front: str,
        back: str,
    ):
        self.mid: NotetypeId | None = None  # Anki's notetype ID
        self.name = name
        self.fields = fields
        self.style = style
        self.front = front
        self.back = back

    def __repr__(self) -> str:
        return f"NoteType({self.name=}, {self.fields=}, {self.front=}, {self.back=})"


# pylint: disable=too-few-public-methods
class FallbackNotetype(AnkiAppNoteType):
    FRONT = "{{Front}}"
    BACK = dedent(
        """\
        {{FrontSide}}

        <hr id=answer>

        {{Back}}"""
    )

    CSS = dedent(
        """\
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }"""
    )

    def __init__(
        self,
        extra_fields: FieldSet = FieldSet(),
        name: str = "AnkiApp Fallback Notetype",
    ) -> None:
        super().__init__(
            name,
            FieldSet(["Front", "Back"]),
            self.CSS,
            self.FRONT,
            self.BACK,
        )
        self.fields |= extra_fields


@dataclasses.dataclass
class AnkiAppDeck:
    did: DeckId | None = dataclasses.field(default=None, init=False)
    ID: str
    name: str
    description: str


@dataclasses.dataclass
class AnkiAppCard:
    layout_id: str
    deck: AnkiAppDeck
    fields: dict[str, str]
    tags: list[str]


# pylint: disable=too-few-public-methods
class AnkiAppMedia:
    def __init__(self, ID: str, mime: str, data: bytes):
        self.ID = ID
        self.mime = mime
        self.ext = guess_extension(mime)
        self.data = data
        self.filename: str | None = None  # Filename in Anki


# pylint: disable=too-few-public-methods,too-many-instance-attributes
class AnkiAppImporter(CopycatImporter):
    name = "AnkiApp"

    def __init__(
        self, mw: AnkiQt, client_id: str, client_token: str, client_version: str
    ):
        super().__init__()
        self.mw = mw
        self.client_id = client_id
        self.client_token = client_token
        self.client_version = client_version
        self.http_client = HttpClient()
        self.decks: dict[str, AnkiAppDeck] = {}
        self.notetypes: dict[str, AnkiAppNoteType] = {}
        self.media: dict[str, AnkiAppMedia] = {}
        self.cards: dict[str, AnkiAppCard] = {}
        self.BLOB_REF_PATTERNS = (
            # Use Anki's HTML media patterns too for completeness
            *(re.compile(p) for p in mw.col.media.html_media_regexps),
            re.compile(r"{{blob (?P<fname>.*?)}}"),
            # AnkiApp uses a form like `<audio id="{blob_id}" type="{mime_type}" />` too
            # TODO: extract the type attribute
            # quoted case
            re.compile(
                r"(?i)(<(?:img|audio)\b[^>]* id=(?P<str>[\"'])(?P<fname>[^>]+?)(?P=str)[^>]*>)"
            ),
            # unquoted case
            re.compile(
                r"(?i)(<(?:img|audio)\b[^>]* id=(?!['\"])(?P<fname>[^ >]+)[^>]*?>)"
            ),
        )

    def _get_request(self, url: str) -> requests.Response:
        return self.http_client.request(
            "GET",
            url,
            headers={
                "ankiapp-client-id": self.client_id,
                "ankiapp-client-token": self.client_token,
                "ankiapp-client-version": self.client_version,
            },
        )

    def _api_get(self, path: str) -> requests.Response:
        response = self._get_request(f"https://api.ankiapp.com/{path}")
        if os.environ.get("DEBUG"):
            from ..consts import consts

            tmp_dir = consts.dir / "tmp" / "requests"
            tmp_dir.mkdir(exist_ok=True, parents=True)
            with open(
                f"{tmp_dir}/{path.replace('/', '_')}.json", "w", encoding="utf-8"
            ) as f:
                f.write(response.text)

        return response

    def _get_media(self, blob_id: str) -> AnkiAppMedia | None:
        try:
            response = self._get_request(f"https://blobs.ankiapp.com/{blob_id}")
            data = response.content
            mime = response.headers.get("content-type")
            if not mime:
                return None
            return AnkiAppMedia(blob_id, mime, data)
        except Exception:
            return None

    def _import_decks(self) -> None:
        from anki.decks import DeckDict, DeckId

        self._update_progress("Fetching decks...")
        for key in ("share", "user", "subscriptions"):
            for deck in self._api_get("decks").json().get(key, []):
                print(deck)
                self.decks[deck["id"]] = AnkiAppDeck(
                    ID=deck["id"],
                    name=deck["name"],
                    description=deck.get("description", ""),
                )
        self._update_progress("Importing decks...")
        for deck in self.decks.values():
            did = DeckId(self.mw.col.decks.add_normal_deck_with_name(deck.name).id)
            deck.did = did
            deck_dict = cast(DeckDict, self.mw.col.decks.get(did))
            if not deck_dict.get("desc"):
                deck_dict["desc"] = deck.description
                self.mw.col.decks.update_dict(deck_dict)

    def _import_cards(self) -> int:
        notes_count = 0
        self._update_progress("Fetching cards...")
        for deck in self.decks.values():
            deck_data = self._api_get(f"decks/{deck.ID}").json()
            deck_layouts = []

            if "config" in deck_data:
                field_names = FieldSet()
                template_fields: list[list[str]] = [[], []]
                for field in deck_data.get("config", {}).get("fields", []):
                    field_names.add(field["name"])
                    for i, side in enumerate(field["sides"]):
                        if side == 1:
                            template_fields[i].append(field_names.get(field["name"]))
                notetype_name = deck.name
                notetype: AnkiAppNoteType
                if any(not t for t in template_fields):
                    notetype = FallbackNotetype(field_names, notetype_name)
                else:
                    notetype = AnkiAppNoteType(
                        notetype_name,
                        field_names,
                        FallbackNotetype.CSS,
                        field_list_to_refs(template_fields[0]),
                        field_list_to_refs(template_fields[1]),
                    )
                self.notetypes[deck.ID] = notetype
                deck_layouts.append(deck.ID)
            else:
                for layout in deck_data.get("layouts", []):
                    name = layout["name"]
                    fields = layout["knol_keys"] or []
                    style = layout["style"] or ""
                    templates = layout["templates"]
                    self.notetypes[layout["id"]] = AnkiAppNoteType(
                        name=name,
                        fields=FieldSet(fields),
                        style=style,
                        front=templates[0],
                        back=templates[1],
                    )
                    deck_layouts.append(layout["id"])

            for knol_data in deck_data.get("knols", []):
                for i, layout_id in enumerate(deck_layouts):
                    self.cards[f'{knol_data["id"]}_{i}'] = AnkiAppCard(
                        layout_id=layout_id,
                        deck=deck,
                        fields=knol_data.get("values", {}),
                        tags=knol_data.get("tags", []),
                    )
                    notes_count += 1

        from anki.models import NotetypeDict

        self._update_progress("Importing notetypes...")
        for notetype in self.notetypes.values():
            model = self.mw.col.models.new(notetype.name)
            for field_name in notetype.fields:
                field_dict = self.mw.col.models.new_field(field_name)
                self.mw.col.models.add_field(model, field_dict)
            template_dict = self.mw.col.models.new_template("Card 1")
            template_dict["qfmt"] = notetype.front
            template_dict["afmt"] = notetype.back
            self.mw.col.models.add_template(model, template_dict)
            model["css"] = notetype.style
            try:
                self.mw.col.models.add(model)
            except Exception:
                logger.error("Failed to add notetype: %s", notetype, exc_info=True)
                raise
            notetype.mid = model["id"]

        self._update_progress("Importing media...")
        for media in self.media.values():
            filename = self.mw.col.media.write_data(media.ID + media.ext, media.data)
            media.filename = filename

        self._update_progress("Importing cards...")
        last_progress = 0.0
        notes_count = 0

        for card in self.cards.values():
            for field_name, contents in card.fields.items():
                for ref_re in self.BLOB_REF_PATTERNS:
                    card.fields[field_name] = ref_re.sub(
                        self._repl_blob_ref, card.fields[field_name]
                    )

            notetype = self.notetypes.get(card.deck.ID, self.notetypes[card.layout_id])
            assert notetype.mid is not None
            model = cast(NotetypeDict, self.mw.col.models.get(notetype.mid))
            assert model is not None
            note = self.mw.col.new_note(model)
            for field_name, contents in card.fields.items():
                normalized_field_name = notetype.fields.get(field_name)
                if normalized_field_name:
                    note[normalized_field_name] = contents
                else:
                    logger.warning(
                        "field '%s' not in notetype '%s' but used in card",
                        field_name,
                        notetype.name,
                    )
            note.tags = card.tags
            assert card.deck.did is not None
            self.mw.col.add_note(note, card.deck.did)
            notes_count += 1
            if time.time() - last_progress >= 0.1:
                self._update_progress(
                    label=f"Imported {notes_count} out of {len(self.cards)} cards",
                    value=notes_count,
                    max=len(self.cards),
                )
                last_progress = time.time()

        return notes_count

    def _cancel_if_needed(self) -> None:
        if self.mw.progress.want_cancel():
            raise CopycatImporterCanceled()

    def _update_progress(
        self, label: str, value: int | None = None, max: int | None = None
    ) -> None:
        def on_main() -> None:
            self.mw.progress.update(label=label, value=value, max=max)

        self.mw.taskman.run_on_main(on_main)
        self._cancel_if_needed()

    def _check_media_mime(self, media: AnkiAppMedia) -> bool:
        if not media.ext:
            self.warnings.append(
                f"unrecognized mime for media file {media.ID}: {media.mime}"
            )
            return False
        return True

    def _repl_blob_ref(self, match: Match[str]) -> str:
        blob_id = match.group("fname")
        media_obj = None
        if blob_id in self.media:
            media_obj = self.media[blob_id]
        else:
            media_obj = self._get_media(blob_id)
            if media_obj and self._check_media_mime(media_obj):
                filename = self.mw.col.media.write_data(
                    media_obj.ID + media_obj.ext, media_obj.data
                )
                media_obj.filename = filename
                self.media[media_obj.ID] = media_obj
        if media_obj and media_obj.filename:
            return fname_to_link(media_obj.filename)
        self.warnings.append(f"Missing media file: {blob_id}")
        # dummy image ref
        return f'<img src="{blob_id}.jpg"></img>'

    def do_import(self) -> int:
        self._import_decks()
        return self._import_cards()
