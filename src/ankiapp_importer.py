import sqlite3
from mimetypes import guess_extension
import urllib
import html
import re
import base64
from typing import TYPE_CHECKING

import aqt.editor

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class NoteType:
    def __init__(self, name, templates, style, fields):
        self.name = name
        # Templates are stored as a string representation of a Python list, apparently
        templates = eval(templates)
        self.front = self._fix_field_refs(templates[0])
        self.back = self._fix_field_refs(templates[1])
        self.style = style
        self.fields = fields

    def _fix_field_refs(self, template):
        # AnkiApp uses `{{[FieldName]}}`
        # FIXME: use a regex instead?
        return template.replace("{{[", "{{").replace("]}}", "}}")

    def __repr__(self):
        return f"NoteType({self.name})"


class Deck:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"Deck({self.name})"


class Card:
    def __init__(self, notetype, deck, fields, tags):
        self.notetype = notetype
        self.deck = deck
        self.fields = fields
        self.tags = tags


# https://github.com/ankitects/anki/blob/main/qt/aqt/editor.py


def fnameToLink(fname):
    ext = fname.split(".")[-1].lower()
    if ext in aqt.editor.pics:
        name = urllib.parse.quote(fname.encode("utf8"))
        return f'<img src="{name}">'
    else:
        return f"[sound:{html.escape(fname, quote=False)}]"


BLOB_REF_RE = re.compile(r"{{blob (.*?)}}")


def repl_blob_ref(importer, match):
    blob_id = match.group(1)
    return fnameToLink(importer.media[blob_id].filename)


class Media:

    # Work around guess_extension() not recognizing some file types
    extensions_for_mimes = {
        "image/webp": ".webp"  # Not recognized (on Windows 10 at least)
    }

    def __init__(self, id, mime, data):
        self.id = id
        self.mime = mime
        self.ext = guess_extension(mime)
        if not self.ext:
            # FIXME: Maybe warn about unrecognized file types
            self.ext = self.extensions_for_mimes.get(mime, ".mp3")
        self.data = base64.b64decode(data)


class AnkiAppImporter:
    def __init__(self, filename):
        self.con = sqlite3.connect(filename)
        self.cur = self.con.cursor()
        self._extract_notetypes()
        self._extract_decks()
        self._extract_media()
        self._extract_cards()

    def _extract_notetypes(self):
        self.notetypes = {}
        for row in self.cur.execute("SELECT * FROM layouts"):
            id, name, templates, style = row[:4]
            fields = set()
            c = self.con.cursor()
            for r in c.execute(
                "SELECT knol_key_name FROM knol_keys_layouts WHERE layout_id = ?", (id,)
            ):
                fields.add(r[0])

            self.notetypes[id] = NoteType(name, templates, style, fields)

    def _extract_decks(self):
        self.decks = {}
        for row in self.cur.execute("SELECT * FROM decks"):
            id = row[0]
            name = row[2]
            description = row[3]
            self.decks[id] = Deck(name, description)

    def _extract_media(self):
        self.media = {}
        for row in self.cur.execute("SELECT id, type, value FROM knol_blobs"):
            id = row[0]
            mime = row[1]
            data = row[2]
            self.media[id] = Media(id, mime, data)

    def _extract_cards(self):
        self.cards = {}
        for row in self.cur.execute("SELECT * FROM cards"):
            id = row[0]
            knol_id = row[1]
            layout_id = row[2]
            notetype = self.notetypes[layout_id]
            c = self.con.cursor()
            c.execute("SELECT deck_id FROM cards_decks WHERE card_id = ?", (id,))
            deck = self.decks[c.fetchone()[0]]
            fields = {}
            for row in c.execute(
                "SELECT knol_key_name, value FROM knol_values WHERE knol_id = ?",
                (knol_id,),
            ):
                # NOTE: Filling empty fields for now to avoid errors on importing empty notes
                # because I've not figured out yet a way to find the order of notetype fields (If any is kept by AnkiApp)
                fields[row[0]] = "&nbsp" if not row[1] else row[1]
            tags = list(
                map(
                    lambda r: r[0],
                    c.execute(
                        "SELECT tag_name FROM knols_tags WHERE knol_id = ?", (knol_id,)
                    ),
                )
            )

            # It seems that sometimes there are field names missing from
            # knol_keys_layouts (processed in _extract_notetypes) even though
            # they have knol_values entries.
            # So we collect all field names we find here and update the notetype accordingly
            notetype.fields.update(fields.keys())

            self.cards[id] = Card(notetype, deck, fields, tags)

    def import_to_anki(self, mw: "AnkiQt") -> int:
        mw.taskman.run_on_main(lambda: mw.progress.update(label="Importing decks..."))
        for deck in self.decks.values():
            did = mw.col.decks.add_normal_deck_with_name(deck.name).id
            deck.id = did
            deck_dict = mw.col.decks.get(did)
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
            notetype.id = model["id"]

        mw.taskman.run_on_main(lambda: mw.progress.update(label="Importing media..."))
        for media in self.media.values():
            filename = mw.col.media.write_data(media.id + media.ext, media.data)
            media.filename = filename

        mw.taskman.run_on_main(lambda: mw.progress.update(label="Importing cards..."))
        notes_count = 0
        for card in self.cards.values():
            for field_name, contents in card.fields.items():
                card.fields[field_name] = BLOB_REF_RE.sub(
                    lambda m: repl_blob_ref(self, m), contents
                )
            note_data = {
                "deck": card.deck.id,
                "model": card.notetype.id,
                "fields": card.fields,
                "tags": card.tags,
            }

            model = mw.col.models.get(note_data["model"])
            note = mw.col.new_note(model)
            for field_name, contents in note_data["fields"].items():
                note[field_name] = contents
            note.set_tags_from_str("".join(note_data["tags"]))
            mw.col.add_note(note, note_data["deck"])
            notes_count += 1

        return notes_count
