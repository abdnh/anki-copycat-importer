# AnkiApp Importer

An [Anki](https://apps.ankiweb.net/) add-on to import decks from the copycat AnkiApp (https://www.ankiapp.com/).

It appears that AnkiApp started to [paywall the deck export feature](https://www.reddit.com/r/Anki/comments/ocbhry/help_to_bypass_ankiapps_paywall_for_deck_export/).
So you can no longer export a zip of your cards [without paying](https://www.ankiapp.com/support/solutions/ddcf01b0/can-i-export-my-flashcards-from-ankiapp-/).

This add-on salvages the cards from the SQLite database and was inspired by the Reddit post linked above.
It can import cards, decks, note types, and media files.

## How to Use

- Download the add-on from https://ankiweb.net/shared/info/2072125761
- Run Anki and go to **Tools > Import From AnkiApp** and choose AnkiApp's database file (`C:\Users\%USERNAME%\AppData\Roaming\AnkiApp\databases\file__0` on Windows; see the Reddit post above for more info).
- Grab a cup of coffee while waiting for importing to finish.

## Notes & Known Issues

- Study progress is not imported.
- AnkiApp doesn't seem to keep any info on the positions of note type fields, so an empty field will cause
  Anki to refuse to import its note if it happened to be imported as the first field.
  To prevent that, the add-on fills all empty fields with a non-breaking space.

## References

- [AnkiApp is not part of the Anki ecosystem - Frequently Asked Questions](https://faqs.ankiweb.net/ankiapp-is-not-part-of-the-anki-ecosystem.html) (with some notes about importing if you have a zip file)
- [Help to bypass Ankiapp's paywall for deck export : Anki | Reddit](https://www.reddit.com/r/Anki/comments/ocbhry/help_to_bypass_ankiapps_paywall_for_deck_export/)
- [AnkiApp - Support | Can I export my flashcards from AnkiApp?](https://www.ankiapp.com/support/solutions/ddcf01b0/can-i-export-my-flashcards-from-ankiapp-/)

## TODO

- [ ] tests

## Support me

Consider supporting me on Ko-fi or Patreon if you like my add-ons:

<a href='https://ko-fi.com/U7U8AE997'><img height='36' src='https://cdn.ko-fi.com/cdn/kofi1.png?v=3' border='0' alt='Buy Me a Coffee at ko-fi.com' /></a> <a href="https://www.patreon.com/abdnh"><img height='36' src="https://i.imgur.com/mZBGpZ1.png"></a>
