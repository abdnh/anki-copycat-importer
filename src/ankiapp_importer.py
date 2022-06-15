import base64
import html
import json
import re
import sqlite3
import urllib
from mimetypes import guess_extension
from typing import Dict, List, Match, Optional, Set, cast

import aqt.editor
from anki.decks import DeckDict, DeckId
from anki.models import NotetypeDict, NotetypeId
from aqt.main import AnkiQt


class NoteType:
    def __init__(self, name: str, templates: str, style: str, fields: Set):
        self.mid: Optional[NotetypeId] = None  # Anki's notetype ID
        self.name = name
        templates = json.loads(templates)
        self.front = self._fix_field_refs(templates[0])
        self.back = self._fix_field_refs(templates[1])
        self.style = style
        self.fields = fields

    def _fix_field_refs(self, template: str) -> str:
        # AnkiApp uses `{{[FieldName]}}`
        # FIXME: use a regex instead?
        return template.replace("{{[", "{{").replace("]}}", "}}")

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
        self.data = base64.b64decode(data)
        self.filename: Optional[str] = None  # Filename in Anki


class AnkiAppImporter:
    def __init__(self, filename: str):
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
            fields = set()
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
            self.media[ID] = Media(ID, mime, data)

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
                fields[row[0]] = "&nbsp" if not row[1] else row[1]
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
            notetype.fields.update(fields.keys())

            self.cards[ID] = Card(notetype, deck, fields, tags)

    BLOB_REF_RE = re.compile(r"{{blob (.*?)}}")

    def _repl_blob_ref(self, match: Match[str]) -> str:
        blob_id = match.group(1)
        try:
            return fname_to_link(self.media[blob_id].filename)
        except KeyError:
            self.warnings.add(f"Missing media file: {blob_id}")
            # dummy image ref
            return f'<img src="{blob_id}.jpg"></img>'

    def import_to_anki(self, mw: AnkiQt) -> int:
        mw.taskman.run_on_main(lambda: mw.progress.update(label="Importing decks..."))
        for deck in self.decks.values():
            did = DeckId(mw.col.decks.add_normal_deck_with_name(deck.name).id)
            deck.did = did
            deck_dict = cast(DeckDict, mw.col.decks.get(did))
            if not deck_dict.get("desc"):
                deck_dict["desc"] = deck.description
                mw.col.decks.update_dict(deck_dict)

        mw.taskman.run_on_main(
            lambda: mw.progress.update(label="Importing notetypes...")
        )
        for notetype in self.notetypes.values():
            model = mw.col.models.new(notetype.name)
            mw.col.models.ensure_name_unique(model)
            for field_name in notetype.fields:
                field_dict = mw.col.models.new_field(field_name)
                mw.col.models.add_field(model, field_dict)
            template_dict = mw.col.models.new_template("Card 1")
            template_dict["qfmt"] = notetype.front
            template_dict["afmt"] = notetype.back
            mw.col.models.add_template(model, template_dict)
            model["css"] = notetype.style
            mw.col.models.add(model)
            notetype.mid = model["id"]

        mw.taskman.run_on_main(lambda: mw.progress.update(label="Importing media..."))
        for media in self.media.values():
            filename = mw.col.media.write_data(media.ID + media.ext, media.data)
            media.filename = filename

        mw.taskman.run_on_main(lambda: mw.progress.update(label="Importing cards..."))
        notes_count = 0
        for card in self.cards.values():
            for field_name, contents in card.fields.items():
                card.fields[field_name] = self.BLOB_REF_RE.sub(
                    self._repl_blob_ref, contents
                )

            assert card.notetype.mid is not None
            model = cast(NotetypeDict, mw.col.models.get(card.notetype.mid))
            note = mw.col.new_note(model)
            for field_name, contents in card.fields.items():
                note[field_name] = contents
            note.set_tags_from_str("".join(card.tags))
            assert card.deck.did is not None
            mw.col.add_note(note, card.deck.did)
            notes_count += 1

        return notes_count
