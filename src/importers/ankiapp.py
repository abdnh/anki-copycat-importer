import base64
import dataclasses
import json
import re
import sqlite3
import time
import zipfile
from collections.abc import Iterable, Iterator, MutableSet
from enum import Enum
from pathlib import Path
from re import Match
from textwrap import dedent
from typing import Any, Dict, List, Optional, cast

import ccl_chromium_indexeddb
import requests
from anki.decks import DeckDict, DeckId
from anki.models import NotetypeDict, NotetypeId
from aqt.main import AnkiQt
from bs4 import BeautifulSoup

from ..appdata import AnkiAppData
from ..config import config
from ..log import logger
from .errors import CopycatImporterCanceled, CopycatImporterError
from .importer import CopycatImporter
from .utils import fname_to_link, guess_extension, guess_mime

INVALID_FIELD_CHARS_RE = re.compile('[:"{}]')


# Must match fix_name in fields.rs: https://github.com/ankitects/anki/blob/404a6c5d4a5fd908a20d8cbdb003c1204e10c0ce/rslib/src/notetype/fields.rs#L55
def fix_field_name(text: str) -> str:
    text = text.strip()
    text = text.lstrip("#/^")
    return INVALID_FIELD_CHARS_RE.sub("", text)


class FieldSet(MutableSet):
    """A set to hold field names in a case-insensitive manner.
    Used to work around some databases containing multiple field names belonging
    to the same layout and only differing in case, which can't be imported to Anki as they are.
    """

    def __init__(self, iterable: Optional[Iterable] = None) -> None:
        self.elements: set[str] = set()
        super().__init__()
        if iterable:
            for el in iterable:
                self.add(el)

    def add(self, value: str) -> None:
        if value not in self:
            self.elements.add(value)

    def discard(self, value: str) -> None:
        for item in self.elements:
            if item.lower() == value.lower():
                self.elements.discard(item)
                return

    def __iter__(self) -> Iterator[str]:
        return iter(self.elements)

    def __len__(self) -> int:
        return len(self.elements)

    def __contains__(self, value: Any) -> bool:
        for item in self.elements:
            if item.lower() == value.lower():
                return True
        return False

    def normalize(self, value: str) -> str:
        """Return `value` as stored in the set if it exists, otherwise return it as it is"""
        for item in self.elements:
            if item.lower() == value.lower():
                return item
        return value

    def __repr__(self) -> str:
        return repr(self.elements)


# pylint: disable=too-many-arguments
class NoteType:
    def __init__(
        self,
        name: str,
        fields: FieldSet,
        style: str,
        front: str,
        back: str,
        from_db: bool = False,
    ):
        self.mid: Optional[NotetypeId] = None  # Anki's notetype ID
        self.name = name
        self.fields = fields
        self.style = style
        self._front = front
        self._back = back
        self._from_db = from_db

    @staticmethod
    def from_db(
        name: str, fields: FieldSet, style: str, templates_str: Optional[str] = None
    ) -> Optional["NoteType"]:
        if not templates_str:
            templates_str = ""
        templates = json.loads(templates_str)
        if not isinstance(templates, list) or len(templates) < 2:
            return None
        return NoteType(name, fields, style, templates[0], templates[1], from_db=True)

    def _transform_raw_template(self, template: str) -> str:
        """Transform AnkiApp's field reference syntax, e.g. `{{[FieldName]}}`"""
        # TODO: use a regex instead?
        template = template.replace("{{[", "{{").replace("]}}", "}}")
        # Unlike Anki, AnkiApp uses case-insensitive references, so we need to fix them
        for field in self.fields:
            template = re.sub(
                r"\{\{(#|/|^)?%s\}\}" % re.escape(field),
                "{{\\1%s}}" % fix_field_name(field),
                template,
                flags=re.IGNORECASE,
            )
        return template

    def front(self) -> str:
        if self._from_db:
            return self._transform_raw_template(self._front)
        return self._front

    def back(self) -> str:
        if self._from_db:
            return self._transform_raw_template(self._back)
        return self._back

    def __repr__(self) -> str:
        return (
            f"NoteType({self.name=}, {self.fields=}, {self.front()=}, {self.back()=})"
        )


# pylint: disable=too-few-public-methods
class FallbackNotetype(NoteType):
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
class Deck:
    did: Optional[DeckId] = dataclasses.field(default=None, init=False)
    ID: str
    name: str
    description: str


@dataclasses.dataclass
class Card:
    layout_id: str
    deck: Deck
    fields: Dict[str, str]
    tags: List[str]


# pylint: disable=too-few-public-methods
class Media:
    # TODO: maybe explicitly close session after we finish
    http_session = requests.Session()

    def __init__(self, ID: str, mime: str, data: bytes):
        self.ID = ID
        self.mime = mime
        self.ext = guess_extension(mime)
        self.data = data
        self.filename: Optional[str] = None  # Filename in Anki

    @classmethod
    def from_server(cls, blob_id: str) -> Optional["Media"]:
        # AnkiApp exposes users' media files in the open - Do not tell anyone!
        # We fall back to this method for files not found in the local database
        # (e.g. in newer AnkiApp versions where files are stored in a separate IndexedDB folder with no apparent method connecting them to the blob IDs)
        try:
            with cls.http_session.get(
                f"https://blobs.ankiapp.com/{blob_id}", timeout=30
            ) as response:
                response.raise_for_status()
                data = response.content
                mime = response.headers.get("content-type")
                if not mime:
                    return None
                return Media(blob_id, mime, data)
        except Exception:
            return None


class IndexedDBReader:
    def __init__(self) -> None:
        self.decks: Dict[str, Dict] = {}

    def _read(self, leveldb_path: Path, blob_path: Path) -> None:
        try:
            db = ccl_chromium_indexeddb.WrappedIndexDB(leveldb_path, blob_path)
            if "DecksDatabase" in db:
                for record in (
                    db["DecksDatabase"]
                    .get_object_store_by_name("decks")
                    .iterate_records()
                ):
                    if record.value and "deckID" in record.value:
                        self.decks[record.value["deckID"]] = record.value
            logger.debug("Decks extracted from IndexedDB: %s", self.decks)
        except Exception:
            logger.error("ccl_chromium_indexeddb failed", exc_info=True)

    def notetype_for_deck(self, deck_id: str, deck_name: str) -> Optional[NoteType]:
        if deck_id not in self.decks:
            return None
        deck = self.decks[deck_id]
        deck_config = deck.get("config", {})
        notetype_name = deck_config.get(
            "name", deck_config.get("base", f"{deck_name} Notetype")
        )
        fields = FieldSet()
        front = ""
        back = ""
        for field in deck_config.get("fields"):
            # TODO: Handle fields with different cases somehow
            if field["name"] in fields:
                continue
            fields.add(field["name"])
            field_ref = "<div>{{%s}}</div>" % field["name"]
            if field["sides"][0]:
                front += field_ref
            if field["sides"][1]:
                back += field_ref

        return NoteType(notetype_name, fields, FallbackNotetype.CSS, front, back)


class ImportedPathType(Enum):
    DATA_DIR = 1
    DB_PATH = 2
    XML_ZIP = 3


@dataclasses.dataclass
class ImportedPathInfo:
    path: Path
    type: ImportedPathType


# pylint: disable=too-few-public-methods,too-many-instance-attributes
class AnkiAppImporter(CopycatImporter):
    name = "AnkiApp"

    def __init__(self, mw: AnkiQt, paths: List[ImportedPathInfo]):
        super().__init__()
        self.mw = mw
        self.warnings: set[str] = set()
        self.decks: Dict[str, Deck] = {}
        self.notetypes: Dict[str, NoteType] = {}
        self.media: Dict[str, Media] = {}
        self.cards: Dict[str, Card] = {}
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
        self.appdata: Optional[AnkiAppData] = None
        self.indexeddb_reader = IndexedDBReader()
        for path_info in paths:
            if path_info.type == ImportedPathType.DATA_DIR:
                self.appdata = AnkiAppData(path_info.path)
                if not self.appdata.sqlite_dbs:
                    raise CopycatImporterError(
                        "Unable to locate database file in data folder."
                    )
                # TODO: maybe import all databases or allow the user to choose
                db_path = self.appdata.sqlite_dbs[0]
                if self.appdata.indexeddb_dbs:
                    self.indexeddb_reader._read(
                        self.appdata.indexeddb_dbs[0][0],
                        self.appdata.indexeddb_dbs[0][1],
                    )
            elif path_info.type == ImportedPathType.DB_PATH:
                db_path = path_info.path
            if path_info.type != ImportedPathType.XML_ZIP:
                self.con = sqlite3.connect(db_path)
                self.mw.progress.update(
                    label="Extracting collection from AnkiApp database...",
                )
                self._extract_notetypes()
                self._extract_decks()
                self._extract_media()
                self._extract_cards()
            else:
                self._extract_xml_zip(path_info.path)

    def _cancel_if_needed(self) -> None:
        if self.mw.progress.want_cancel():
            raise CopycatImporterCanceled

    def _update_progress(
        self, label: str, value: Optional[int] = None, max: Optional[int] = None
    ) -> None:
        def on_main() -> None:
            self.mw.progress.update(label=label, value=value, max=max)

        self.mw.taskman.run_on_main(on_main)
        self._cancel_if_needed()

    def _extract_notetypes(self) -> None:
        self._update_progress("Extracting notetypes...")
        for row in self.con.execute("SELECT * FROM layouts"):
            ID, name, templates, style = row[:4]
            ID = str(ID)
            fields = FieldSet()
            for row in self.con.execute(
                "SELECT knol_key_name FROM knol_keys_layouts WHERE layout_id = ?", (ID,)
            ):
                fields.add(row[0])
            notetype = NoteType.from_db(name, fields, style, templates)
            if not notetype:
                notetype = FallbackNotetype(fields)
            if notetype:
                self.notetypes[ID] = notetype
            self._cancel_if_needed()

    def _extract_decks(self) -> None:
        self._update_progress("Extracting decks...")
        for row in self.con.execute("SELECT * FROM decks"):
            ID = row[0]
            name = row[2]
            description = row[3]
            self.decks[ID] = Deck(ID, name, description)
            self._cancel_if_needed()

    def _check_media_mime(self, media: Media) -> bool:
        if not media.ext:
            self.warnings.add(
                f"unrecognized mime for media file {media.ID}: {media.mime}"
            )
            return False
        return True

    def _extract_media(self) -> None:
        self._update_progress("Extracting media...")
        for row in self.con.execute("SELECT id, type, value FROM knol_blobs"):
            ID = str(row[0])
            mime = row[1]
            data = row[2]
            media = Media(ID, mime, base64.b64decode(data))
            if self._check_media_mime(media):
                self.media[ID] = media
            self._cancel_if_needed()

    def _extract_cards(self) -> None:
        self._update_progress("Extracting cards...")
        for row in self.con.execute(
            "select c.id, c.knol_id, c.layout_id, d.deck_id from cards c, cards_decks d where c.id = d.card_id"
        ):
            ID = row[0]
            knol_id = row[1]
            layout_id = str(row[2])
            deck_id = str(row[3])
            deck = self.decks[deck_id]
            notetype = None
            if deck_id in self.notetypes:
                # Fetched from IndexedDB below
                notetype = self.notetypes[deck_id]
                logger.debug(
                    "Using notetype fetched from IndexedDB for card_id=%s: %s",
                    ID,
                    notetype,
                )
            elif layout_id not in self.notetypes:
                notetype = self.indexeddb_reader.notetype_for_deck(deck_id, deck.name)
                logger.debug(
                    "Notetype fetched from IndexedDB for layout_id=%s, card_id=%s: %s",
                    layout_id,
                    ID,
                    notetype,
                )
                if not notetype:
                    notetype = FallbackNotetype()
                    self.notetypes[layout_id] = notetype
                self.notetypes[layout_id] = notetype
            elif isinstance(self.notetypes[layout_id], FallbackNotetype):
                logger.debug(
                    "Fallback notetype for layout_id=%s, card_id=%s: %s",
                    layout_id,
                    ID,
                    self.notetypes[layout_id],
                )
                notetype = self.indexeddb_reader.notetype_for_deck(deck_id, deck.name)
                logger.debug(
                    "Notetype fetched from IndexedDB for card_id=%s, deck_id=%s: %s",
                    ID,
                    deck_id,
                    notetype,
                )
                if not notetype:
                    notetype = self.notetypes[layout_id]
                self.notetypes[deck_id] = notetype
            else:
                notetype = self.notetypes[layout_id]
                logger.debug(
                    "Using notetype fetched from SQLite for card_id=%s, deck_id=%s: %s",
                    ID,
                    deck_id,
                    notetype,
                )

            fields: Dict[str, str] = {}
            for row in self.con.execute(
                "SELECT knol_key_name, value FROM knol_values WHERE knol_id = ?",
                (knol_id,),
            ):
                field_name = notetype.fields.normalize(row[0])
                # Avoid overriding previously processed non-empty fields differing only in case
                # FIXME: we should instead add new fields with unique names to avoid data loss
                if not fields.get(field_name, "").strip().replace("&nbsp", ""):
                    # NOTE: Filling empty fields with a non-breaking space for now to avoid errors on importing empty notes
                    # because I've not figured out yet a way to find the order of notetype fields
                    # (If any is kept by AnkiApp)
                    fields[field_name] = "&nbsp" if not row[1] else row[1]
            tags = [
                r[0]
                for r in self.con.execute(
                    "SELECT tag_name FROM knols_tags WHERE knol_id = ?", (knol_id,)
                )
            ]

            # It seems that sometimes there are field names missing from
            # knol_keys_layouts (processed in _extract_notetypes) even though
            # they have knol_values entries.
            # So we collect all field names we find here and update the notetype accordingly
            notetype.fields |= fields.keys()

            self.cards[ID] = Card(layout_id, deck, fields, tags)
            self._cancel_if_needed()

    def _repl_blob_ref(self, match: Match[str]) -> str:
        blob_id = match.group("fname")
        media_obj = None
        if blob_id in self.media:
            media_obj = self.media[blob_id]
        elif config.importer_options("ankiapp").get("remote_media", True):
            media_obj = Media.from_server(blob_id)
            if media_obj and self._check_media_mime(media_obj):
                filename = self.mw.col.media.write_data(
                    media_obj.ID + media_obj.ext, media_obj.data
                )
                media_obj.filename = filename
                self.media[media_obj.ID] = media_obj
        if media_obj and media_obj.filename:
            return fname_to_link(media_obj.filename)
        self.warnings.add(f"Missing media file: {blob_id}")
        # dummy image ref
        return f'<img src="{blob_id}.jpg"></img>'

    deck_id = 1
    card_id = 1

    def _extract_xml_zip(self, path: Path) -> None:
        # pylint: disable=too-many-locals
        def _read_xml(buffer: bytes) -> None:
            def field_list_to_refs(flds: List[str]) -> str:
                return "<br>".join("{{%s}}" % f for f in flds)

            soup = BeautifulSoup(buffer, "html.parser")
            for deck_el in soup.select("deck"):
                deck = Deck(str(self.deck_id), str(deck_el["name"]), "")
                self.decks[str(self.deck_id)] = deck
                field_names = FieldSet()
                template_fields: List[List[str]] = [[], []]
                for field in deck_el.select("fields > *"):
                    field_names.add(str(field["name"]))
                    for i, side in enumerate(field["sides"]):
                        if side == "1":
                            template_fields[i].append(str(field["name"]))
                notetype_name = f"{deck.name} Notetype"
                notetype: NoteType
                if any(not t for t in template_fields):
                    notetype = FallbackNotetype(field_names, notetype_name)
                else:
                    notetype = NoteType(
                        notetype_name,
                        field_names,
                        FallbackNotetype.CSS,
                        field_list_to_refs(template_fields[0]),
                        field_list_to_refs(template_fields[1]),
                    )
                self.notetypes[str(self.deck_id)] = notetype
                for card_el in deck_el.select("card"):
                    fields: Dict[str, str] = {}
                    for field in card_el.select("field"):
                        fields[
                            notetype.fields.normalize(str(field["name"]))
                        ] = field.decode_contents()
                    notetype.fields |= fields.keys()
                    card = Card(str(self.deck_id), deck, fields, [])
                    self.cards[str(self.card_id)] = card
                    self.card_id += 1
                self.deck_id += 1

        with zipfile.ZipFile(path, "r") as file:
            for info in file.infolist():
                if info.filename.endswith(".xml"):
                    with file.open(info) as xml_file:
                        _read_xml(xml_file.read())
                elif info.filename.startswith("blobs/"):
                    blob_id = info.filename.split("blobs/", maxsplit=1)[1]
                    if not blob_id:
                        continue
                    with file.open(info, "r") as media_file:
                        data = media_file.read()
                        try:
                            mime = guess_mime(data)
                            if mime:
                                media = Media(blob_id, mime, data)
                                if self._check_media_mime(media):
                                    self.media[blob_id] = media
                        except Exception as exc:
                            basename = info.filename.split("blobs/")[1]
                            self.warnings.add(
                                f"Failed to detect type of media file {basename}: {exc}"
                            )

    # pylint: disable=too-many-locals
    def do_import(self) -> int:
        self._update_progress("Importing decks...")
        for deck in self.decks.values():
            did = DeckId(self.mw.col.decks.add_normal_deck_with_name(deck.name).id)
            deck.did = did
            deck_dict = cast(DeckDict, self.mw.col.decks.get(did))
            if not deck_dict.get("desc"):
                deck_dict["desc"] = deck.description
                self.mw.col.decks.update_dict(deck_dict)

        self._update_progress("Importing notetypes...")
        for notetype in self.notetypes.values():
            model = self.mw.col.models.new(notetype.name)
            for field_name in notetype.fields:
                field_dict = self.mw.col.models.new_field(field_name)
                self.mw.col.models.add_field(model, field_dict)
            template_dict = self.mw.col.models.new_template("Card 1")
            template_dict["qfmt"] = notetype.front()
            template_dict["afmt"] = notetype.back()
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
                note[fix_field_name(field_name)] = contents
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
