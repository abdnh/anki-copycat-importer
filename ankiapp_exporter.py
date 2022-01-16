import sqlite3

from ankiconnect import ankiconnect


class NoteType:
    def __init__(self, id, name, templates, style, fields):
        self.id = id
        self.name = name
        # Templates are stored as a string representation of a Python list, apparently
        templates = eval(templates)
        self.front = self._fix_field_refs(templates[0])
        self.back = self._fix_field_refs(templates[1])
        self.style = style
        self.fields = fields

    def _fix_field_refs(self, template):
        # AnkiApp uses `{{[FieldName]}}`
        return template.replace("{{[", "{{").replace("]}}", "}}")

    def __str__(self):
        return f"NoteType({self.name})"


class Deck:
    def __init__(self, id, name, description):
        self.id = id
        self.name = name
        self.description = description  # FIXME: not imported yet

    def __str__(self):
        return f"Deck({self.name})"


class Card:
    def __init__(self, id, notetype, deck, fields, tags):
        self.id = id
        self.notetype = notetype
        self.deck = deck
        self.fields = fields
        self.tags = tags


class AnkiAppExporter:
    def __init__(self, filename):
        self.con = sqlite3.connect(filename)
        self.cur = self.con.cursor()
        self._export_notetypes()
        self._export_decks()
        self._export_cards()

    def _export_notetypes(self):
        self.notetypes = {}
        for row in self.cur.execute('SELECT * FROM layouts'):
            id, name, templates, style = row[:4]
            fields = []
            c = self.con.cursor()
            for r in c.execute('SELECT knol_key_name FROM knol_keys_layouts WHERE layout_id = ?', (id,)):
                fields.append(r[0])
            self.notetypes[id] = NoteType(id, name, templates, style, fields)
            # print(id, fields)
            # print(row)

    def _export_decks(self):
        self.decks = {}
        for row in self.cur.execute('SELECT * FROM decks'):
            id = row[0]
            name = row[2]
            description = row[3]
            self.decks[id] = Deck(id, name, description)
            # print(id, name, description)

    def _export_cards(self):
        self.cards = {}
        for row in self.cur.execute('SELECT * FROM cards'):
            id = row[0]
            knol_id = row[1]
            layout_id = row[2]
            notetype = self.notetypes[layout_id]
            c = self.con.cursor()
            c.execute('SELECT deck_id FROM cards_decks WHERE card_id = ?', (id,))
            deck = self.decks[c.fetchone()[0]]
            fields = {}
            for row in c.execute('SELECT knol_key_name, value FROM knol_values WHERE knol_id = ?', (knol_id,)):
                # NOTE: Filling empty fields for now to avoid errors on importing empty notes
                # because I've not figured out yet a way to find the order of notetype fields (If any is kept by AnkiApp)
                fields[row[0]] = '&nbsp' if not row[1] else row[1]
            tags = list(map(lambda r: r[0], c.execute(
                'SELECT tag_name FROM knols_tags WHERE knol_id = ?', (knol_id,))))

            self.cards[id] = Card(id, notetype, deck, fields, tags)
            # print(id, notetype, deck, fields, tags)

    def import_to_anki(self):
        for deck in self.decks.values():
            deck_id = ankiconnect('createDeck', deck=deck.name)
            deck.anki_id = deck_id
        for notetype in self.notetypes.values():
            templates = [
                {
                    "Front": notetype.front,
                    "Back": notetype.back,
                }
            ]
            # print(notetype.name)
            # print(templates)
            # FIXME: we should uniqify model name before creating as AnkiApp apparently allows models with identical names (?)
            result = ankiconnect('createModel',
                                 modelName=notetype.name,
                                 inOrderFields=notetype.fields,
                                 cardTemplates=templates,
                                 css=notetype.style)
            notetype.anki_id = result['id']

        notes = []
        for card in self.cards.values():
            note = {
                'deckName': card.deck.name,
                'modelName': card.notetype.name,
                'fields': card.fields,
                'tags': card.tags
            }
            notes.append(note)
        try:
            ankiconnect('addNotes', notes=notes)
        except Exception as ex:
            print(ex)


if __name__ == '__main__':
    exporter = AnkiAppExporter(input('path of database file to import: '))
    exporter.import_to_anki()
