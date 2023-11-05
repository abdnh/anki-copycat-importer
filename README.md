# Copycat Importer

An [Anki](https://apps.ankiweb.net/) add-on to import decks from copycat apps such as [AnkiApp](https://www.ankiapp.com/) and [AnkiPro](https://ankipro.net/).

## AnkiApp

It appears that AnkiApp started to [paywall the deck export feature](https://www.reddit.com/r/Anki/comments/ocbhry/help_to_bypass_ankiapps_paywall_for_deck_export/).
So you can no longer export a zip of your cards [without paying](https://www.ankiapp.com/support/solutions/ddcf01b0/can-i-export-my-flashcards-from-ankiapp-/).

This add-on salvages the cards from the SQLite database and was inspired by the Reddit post linked above. It can import cards, decks, note types, and media files.

![AnkiApp Importer](images/ankiapp.png)

### Usage

-   Make sure all your AnkiApp decks are downloaded before using the add-on. For that, go to AnkiApp, click on each of your decks, then click on the Download button at the bottom if it's shown.
-   Run Anki and go to _Tools > Copycat Importer > Import from AnkiApp_. The add-on tries to detect AnkiApp's data folder on your system automatically. If you see the "Data folder" field already populated, you can go ahead and click Import. You can also specify a different folder location, or a single SQLite database file by checking the "Database file" option (only recommened if you don't have access to the whole data folder for some reason, as the add-on may need other files in the data folder to properly import notetypes).

### Notes & Known Issues

-   Study progress is not imported.
-   AnkiApp doesn't seem to keep any info on the positions of note type fields, so an empty field will cause
    Anki to refuse to import its note if it happened to be imported as the first field.
    To prevent that, the add-on fills all empty fields with a non-breaking space.

## AnkiPro

![AnkiPro Importer](images/ankipro.png)

### Usage

The add-on works by downloading your decks from the AnkiPro site, so it needs your email and password. Go to _Tools > Copycat Importer > Import from AnkiPro_ and enter your account details.

### Notes & Known Issues

-   Importing of [library decks](https://ankipro.net/library) is not supported. Since they are simply scraped from AnkiWeb, you can search and download the decks from [AnkiWeb](https://ankiweb.net/shared/decks) instead.
-   Importing of study progress and deck options is not supported yet.

## Download

You can download the add-on from AnkiWeb: [2072125761](https://ankiweb.net/shared/info/2072125761)

## References

-   [AnkiApp is not part of the Anki ecosystem - Frequently Asked Questions](https://faqs.ankiweb.net/ankiapp-is-not-part-of-the-anki-ecosystem.html) (with some notes about importing if you have a zip file)
-   [Help to bypass Ankiapp's paywall for deck export : Anki | Reddit](https://www.reddit.com/r/Anki/comments/ocbhry/help_to_bypass_ankiapps_paywall_for_deck_export/)
-   [AnkiApp - Support | Can I export my flashcards from AnkiApp?](https://www.ankiapp.com/support/solutions/ddcf01b0/can-i-export-my-flashcards-from-ankiapp-/)
-   [AnkiPro: Another ripoff Anki app - AnkiMobile (iPhone/iPad) - Anki Forums](https://forums.ankiweb.net/t/ankipro-another-ripoff-anki-app/11791)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes.

## Support & feature requests

Please post any questions, bug reports, or feature requests in the [support page](https://forums.ankiweb.net/t/ankiapp-importer/16734/) or the [issue tracker](https://github.com/abdnh/anki-copycat-importer/issues).

If you want priority support for your feature/help request, I'm available for hire.
You can get in touch from the aforementioned pages, via [email](mailto:abdo@abdnh.net) or on [Fiverr](https://www.fiverr.com/abd_nh).

## Support me

Consider supporting me if you like my work:

<a href="https://github.com/sponsors/abdnh"><img height='36' src="https://i.imgur.com/dAgtzcC.png"></a>
<a href="https://www.patreon.com/abdnh"><img height='36' src="https://i.imgur.com/mZBGpZ1.png"></a>
<a href="https://www.buymeacoffee.com/abdnh" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-blue.png" alt="Buy Me A Coffee" style="height: 36px" ></a>

I'm also available for freelance add-on development on Fiverr:

<a href="https://www.fiverr.com/abd_nh/develop-an-anki-addon"><img height='36' src="https://i.imgur.com/0meG4dk.png"></a>
