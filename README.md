# AnkiApp Exporter

An ad-hoc Python program to export decks to Anki (https://apps.ankiweb.net/) from the copycat AnkiApp (https://www.ankiapp.com/)

It appears that AnkiApp started to [paywall the deck export functionality](https://www.reddit.com/r/Anki/comments/ocbhry/help_to_bypass_ankiapps_paywall_for_deck_export/).
So you can no longer export a zip of your cards [without paying](https://www.ankiapp.com/support/solutions/ddcf01b0/can-i-export-my-flashcards-from-ankiapp-/).

This program salvages the cards from the SQLite database and was inspired by the Reddit post linked above.

## How to Use

- Install the AnkiConnect add-on: https://ankiweb.net/shared/info/2055492159
- Install Python: https://www.python.org/downloads/
- Run [ankiapp_exporter.py](ankiapp_exporter.py). You'll prompted for the path of the database file (`C:\Users\%USERNAME%\AppData\Roaming\AnkiApp\databases\file__0` on Windows; see the Reddit post above for more info).
- You should have your decks, notetypes, and cards in Anki now.

## Notes & Known Issues
- Study progress is not exported.

## References

- [AnkiApp is not part of the Anki ecosystem - Frequently Asked Questions](https://faqs.ankiweb.net/ankiapp-is-not-part-of-the-anki-ecosystem.html) (with some notes about importing if you have a zip file)
- [Help to bypass Ankiapp's paywall for deck export : Anki | Reddit](https://www.reddit.com/r/Anki/comments/ocbhry/help_to_bypass_ankiapps_paywall_for_deck_export/)
- [AnkiApp - Support | Can I export my flashcards from AnkiApp?](https://www.ankiapp.com/support/solutions/ddcf01b0/can-i-export-my-flashcards-from-ankiapp-/)