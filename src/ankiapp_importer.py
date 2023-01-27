import base64
import html
import json
import re
import sqlite3
import urllib
from collections.abc import MutableSet
from mimetypes import guess_extension
from typing import Any, Dict, Iterator, List, Match, Optional, Set, cast

import aqt.editor
import requests
from anki.decks import DeckDict, DeckId
from anki.models import NotetypeDict, NotetypeId
from aqt.main import AnkiQt


class FieldSet(MutableSet):
    """A set to hold field names in a case-insensitive manner.
    Used to work around some databases containing multiple field names belonging
    to the same layout and only differing in case, which can't be imported to Anki as they are.
    """

    def __init__(self) -> None:
        self.elements: Set[str] = set()
        super().__init__()

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


class NoteType:
    def __init__(self, name: str, templates: str, style: str, fields: FieldSet):
        self.mid: Optional[NotetypeId] = None  # Anki's notetype ID
        self.name = name
        self._raw_templates = json.loads(templates)
        self.style = style
        self.fields = fields

    def _process_template(self, template: str) -> str:
        # Transform AnkiApp's field reference syntax, e.g. `{{[FieldName]}}`
        # FIXME: use a regex instead?
        template = template.replace("{{[", "{{").replace("]}}", "}}")
        # Unlike Anki, AnkiApp uses case-insensitive references, so we need to fix them
        for field in self.fields:
            template = re.sub(
                r"\{\{%s\}\}" % re.escape(field),
                "{{%s}}" % field,
                template,
                flags=re.IGNORECASE,
            )
        return template

    @property
    def front(self) -> str:
        return self._process_template(self._raw_templates[0])

    @property
    def back(self) -> str:
        return self._process_template(self._raw_templates[1])

    def __repr__(self) -> str:
        return f"NoteType({self.name})"


class Deck:
    def __init__(self, name: str, description: str):
        self.did: Optional[DeckId] = None  # Anki's deck ID
        self.name = name
        self.description = description

    def __repr__(self) -> str:
        return f"Deck({self.name})"


class Card:
    def __init__(
        self, notetype: NoteType, deck: Deck, fields: Dict[str, str], tags: List[str]
    ):
        self.notetype = notetype
        self.deck = deck
        self.fields = fields
        self.tags = tags


# https://github.com/ankitects/anki/blob/main/qt/aqt/editor.py


def fname_to_link(fname: str) -> str:
    ext = fname.split(".")[-1].lower()
    if ext in aqt.editor.pics:
        name = urllib.parse.quote(fname.encode("utf8"))
        return f'<img src="{name}">'
    return f"[sound:{html.escape(fname, quote=False)}]"


class Media:

    # Work around guess_extension() not recognizing some file types
    extensions_for_mimes = {
        # .webp is not recognized on Windows without additional software
        # (https://storage.googleapis.com/downloads.webmproject.org/releases/webp/WebpCodecSetup.exe)
        "image/webp": ".webp",
        "image/jp2": ".jp2",
    }

    # TODO: maybe explicitly close session after we finish
    http_session = requests.Session()

    def __init__(self, ID: str, mime: str, data: bytes):
        self.ID = ID
        self.mime = mime
        ext = guess_extension(mime)
        if not ext:
            try:
                ext = self.extensions_for_mimes[mime]
            except KeyError as exc:
                raise Exception(f"unrecognized mime type: {mime}") from exc
        self.ext = cast(str, ext)
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


class AnkiAppImporter:
    def __init__(self, mw: AnkiQt, filename: str):
        self.mw = mw
        self.con = sqlite3.connect(filename)
        self._extract_notetypes()
        self._extract_decks()
        self._extract_media()
        self._extract_cards()
        self.warnings: Set[str] = set()

    def _extract_notetypes(self) -> None:
        self.notetypes: Dict[bytes, NoteType] = {}
        for row in self.con.execute("SELECT * FROM layouts"):
            ID, name, templates, style = row[:4]
            fields = FieldSet()
            for row in self.con.execute(
                "SELECT knol_key_name FROM knol_keys_layouts WHERE layout_id = ?", (ID,)
            ):
                fields.add(row[0])

            self.notetypes[ID] = NoteType(name, templates, style, fields)

    def _extract_decks(self) -> None:
        self.decks: Dict[bytes, Deck] = {}
        for row in self.con.execute("SELECT * FROM decks"):
            ID = row[0]
            name = row[2]
            description = row[3]
            self.decks[ID] = Deck(name, description)

    def _extract_media(self) -> None:
        self.media: Dict[str, Media] = {}
        for row in self.con.execute("SELECT id, type, value FROM knol_blobs"):
            ID = str(row[0])
            mime = row[1]
            data = row[2]
            self.media[ID] = Media(ID, mime, base64.b64decode(data))

    def _extract_cards(self) -> None:
        self.cards: Dict[bytes, Card] = {}
        for row in self.con.execute("SELECT * FROM cards"):
            ID = row[0]
            knol_id = row[1]
            layout_id = row[2]
            notetype = self.notetypes[layout_id]
            deck_id = self.con.execute(
                "SELECT deck_id FROM cards_decks WHERE card_id = ?", (ID,)
            ).fetchone()[0]
            deck = self.decks[deck_id]
            fields = {}
            for row in self.con.execute(
                "SELECT knol_key_name, value FROM knol_values WHERE knol_id = ?",
                (knol_id,),
            ):
                # NOTE: Filling empty fields for now to avoid errors on importing empty notes
                # because I've not figured out yet a way to find the order of notetype fields
                # (If any is kept by AnkiApp)
                fields[notetype.fields.normalize(row[0])] = (
                    "&nbsp" if not row[1] else row[1]
                )
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

            self.cards[ID] = Card(notetype, deck, fields, tags)

    BLOB_REF_RE = re.compile(r"{{blob (.*?)}}")

    def _repl_blob_ref(self, match: Match[str]) -> str:
        blob_id = match.group(1)
        if blob_id in self.media:
            media_obj = self.media[blob_id]
        else:
            media_obj = Media.from_server(blob_id)
            if media_obj:
                filename = self.mw.col.media.write_data(
                    media_obj.ID + media_obj.ext, media_obj.data
                )
                media_obj.filename = filename
                self.media[media_obj.ID] = media_obj
        if media_obj:
            return fname_to_link(media_obj.filename)
        self.warnings.add(f"Missing media file: {blob_id}")
        # dummy image ref
        return f'<img src="{blob_id}.jpg"></img>'

    def import_to_anki(self) -> int:
        self.mw.taskman.run_on_main(
            lambda: self.mw.progress.update(label="Importing decks...")
        )
        for deck in self.decks.values():
            did = DeckId(self.mw.col.decks.add_normal_deck_with_name(deck.name).id)
            deck.did = did
            deck_dict = cast(DeckDict, self.mw.col.decks.get(did))
            if not deck_dict.get("desc"):
                deck_dict["desc"] = deck.description
                self.mw.col.decks.update_dict(deck_dict)

        self.mw.taskman.run_on_main(
            lambda: self.mw.progress.update(label="Importing notetypes...")
        )
        for notetype in self.notetypes.values():
            model = self.mw.col.models.new(notetype.name)
            self.mw.col.models.ensure_name_unique(model)
            for field_name in notetype.fields:
                field_dict = self.mw.col.models.new_field(field_name)
                self.mw.col.models.add_field(model, field_dict)
            template_dict = self.mw.col.models.new_template("Card 1")
            template_dict["qfmt"] = notetype.front
            template_dict["afmt"] = notetype.back
            self.mw.col.models.add_template(model, template_dict)
            model["css"] = notetype.style
            self.mw.col.models.add(model)
            notetype.mid = model["id"]

        self.mw.taskman.run_on_main(
            lambda: self.mw.progress.update(label="Importing media...")
        )
        for media in self.media.values():
            filename = self.mw.col.media.write_data(media.ID + media.ext, media.data)
            media.filename = filename

        # TODO: maybe report media download progress
        self.mw.taskman.run_on_main(
            lambda: self.mw.progress.update(label="Importing cards...")
        )
        notes_count = 0
        for card in self.cards.values():
            for field_name, contents in card.fields.items():
                card.fields[field_name] = self.BLOB_REF_RE.sub(
                    self._repl_blob_ref, contents
                )

            assert card.notetype.mid is not None
            model = cast(NotetypeDict, self.mw.col.models.get(card.notetype.mid))
            note = self.mw.col.new_note(model)
            for field_name, contents in card.fields.items():
                note[field_name] = contents
            note.set_tags_from_str("".join(card.tags))
            assert card.deck.did is not None
            self.mw.col.add_note(note, card.deck.did)
            notes_count += 1

        return notes_count
