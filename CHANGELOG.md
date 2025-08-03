# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.4] - 2025-08-03

### Fixed

- Fix error with some Noji collections.

## [3.2.3] - 2025-06-18

### Fixed

- Fix only ~20 cards being imported in each AnkiPro deck.

## [3.2.2] - 2025-06-18

### Fixed

- Fix some AnkiPro cards being impored multiple times.
- Fix some AnkiPro cards being incorrectly skipped.

## [3.2.1] - 2025-06-07

### Changed

- Use AnkiPro's new website ([noji.io](https://noji.io/)).

## [3.2.0] - 2025-05-30

### Added

- Support AnkiPro's cloze and TTS cards.

### Fixed

## [3.1.5] - 2025-02-03

### Fixed

- Fix error with some Basic notetypes.

## [3.1.4] - 2024-09-19

### Fixed

- Fixed incomplete importing of AnkiPro decks.

## [3.1.3] - 2024-09-09

### Fixed

- Support importing AnkiPro's library decks.

## [3.1.2] - 2024-08-03

### Fixed

- Fixed incomplete import of AnkiPro notes.
- Fixed AnkiPro media importing.

## [3.1.1] - 2024-08-03

### Fixed

- Fixed AnkiPro importing getting infinitely stuck.

## [3.1.0] - 2024-07-23

### Fixed

- Handle AnkiApp's 'BackSide' special field

### Added

- Added a config option to disable media download.

## [3.0.5] - 2024-07-22

### Fixed

- Fixed some AnkiApp media files not being correctly imported.

## [3.0.4] - 2024-07-21

### Fixed

- Fixed error on missing AnkiPro media files
- Fixed remote AnkiApp media links being reported as missing files.

## [3.0.3] - 2024-06-12

### Fixed

- Fixed AnkiApp importing error caused by field references not being properly handled.

## [3.0.2] - 2024-05-28

### Fixed

- Fixed error after AnkiApp login in non-debug environments.

## [3.0.1] - 2024-05-28

### Fixed

- Fixed error when AnkiApp login button is clicked.

## [3.0.0] - 2024-05-28

### Added

- The add-on now works by downloading your AnkiApp decks from your account. All old importing methods were removed.

## [2.3.1] - 2024-05-19

### Added

- The add-on now reports unexpected errors automatically to me to help debug issues.

## [2.3.0] - 2024-04-27

### Added

- Added a text field for AnkiPro login token and a link to the [AnkiPro Export Helper](https://chromewebstore.google.com/detail/ankipro-export-helper/ghmmlnlfpghgbecgkiananhlbfakmcpd) Chrome extension.

## [2.2.4] - 2024-04-09

### Fixed

- Fixed broken XML importing in last release.

## [2.2.3] - 2024-04-05

### Fixed

- Fixed AnkiPro login no longer working.
- Fixed AnkiApp XML importer adding empty notes.

## [2.2.2] - 2024-03-18

### Fixed

- Fixed an error with field names that start with a number.

## [2.2.1] - 2023-12-30

### Fixed

- Fix error on unrecognized types of downloaded AnkiApp media.
- Fixed m4a files not being recognized.

## [2.2.0] - 2023-11-23

### Added

- Login to AnkiPro via Google and Apple is now supported.

## [2.1.2] - 2023-11-18

### Fixed

- Report media type detection errors

## [2.1.1] - 2023-11-14

### Fixed

- Fixed default AnkiApp data folder not being usable due to the error message "Paths are empty or don't exist".

## [2.1.0] - 2023-11-10

### Added

- Added support for importing AnkiApp's XML zips.

### Fixed

- Do not abort import when unrecognized media types are found.

## [2.0.0] - 2023-11-05

### Added

- The add-on now supports importing decks from [AnkiPro](https://ankipro.net). The add-on's name has been changed to "Copycat Importer" to reflect that.

### Fixed

- Fixed error when no database file path is chosen.

## [1.6.0] - 2023-09-23

### Added

- Added a graphical interface to make it easier to locate AnkiApp's data folder or database.
- The add-on now tries to detect AnkiApp's data folder on your system for you.
- The add-on now keeps some logs under th user_files/logs subfolder.
- Add the ability to extract misssing AnkiApp layouts from IndexedDB databases in the data folder. This is experimental and doesn't work currently on the latest Anki version (2.1.66) due to [an issue](https://github.com/abdnh/anki-copycat-importer/issues/5).

## [1.5.8] - 2023-09-20

### Fixed

- Fixed media importing broken for some users.

## [1.5.7] - 2023-09-17

### Fixed

- Fixed audio references in the form `<audio id="{blob_id}"/>` not being imported.

## [1.5.6] - 2023-08-25

### Fixed

- Work around mp3 files not being recognized on some systems.

## [1.5.5] - 2023-03-03

### Fixed

- Improve the previous fix for field names differing only in case by also stripping non-breaking spaces.

## [1.5.4] - 2023-03-03

### Fixed

- Fixed an issue where the add-on fails to import some fields if the notetype happens to have field names differing only in case.
- Greatly optimize the cards extraction step for large collection.

## [1.5.3] - 2023-02-22

### Fixed

- Handle conditional field references.
- Handle invalid characters in field names (e.g. `:"{}]`)
- Improve handling of notetypes with empty templates. You may notice notetypes with names starting with "AnkiApp Fallback Notetype" after importing. You may need to modify the templates of such notetypes according to your fields as basic templates are used as a fallback.

## [1.5.2] - 2023-02-16

### Fixed

- Fix Basic notetype fallback not working in some cases (again).

## [1.5.1] - 2023-02-13

### Fixed

- Work around fix for notetypes with missing templates not working in collections with no Basic notetype.

## [1.5.0] - 2023-01-29

### Added

- Add a config option to disable remote media fetching.
- Allow cancelling importing and implement more detailed progress updates.

### Fixed

- Fix a regression when there are missing (but used) fields in the layouts table.
- Try to handle notetypes with missing templates by converting their notes to basic ones.

## [1.4.1] - 2022-12-19

### Fixed

- Fix issue with AnkiApp templates containing field references that differ in case from how the fields are actually named.

## [1.4.0] - 2022-10-22

### Added

- Work around media importing not working for newer AnkiApp versions (tested on 6.1.0).
  Importing may take longer to complete, as the add-on now falls back to downloading media directly from AnkiApp's servers in case it can't find them in the local database. See [this forum post](https://forums.ankiweb.net/t/ankiapp-importer/16734/39).

## [1.3.1] - 2022-07-01

### Fixed

- Fixed AnkiApp database file not being selectable in macOS's file selector.

### Added

- Added a note about empty collections.

## [1.3.0] - 2022-04-15

### Added

- Handle missing media files and warn about them.

## [1.2.0] - 2022-03-05

### Added

- Show progress dialog and the number of imported notes.

### Fixed

- Fix for some image formats not being recognized.
- Fix import error on some collections with missing field names in the `layouts` table.

## [1.1.0] - 2022-01-21

### Added

- Deck description is now imported.

## [1.0.0] - 2022-01-17

Initial release

[3.2.4]: https://github.com/abdnh/anki-copycat-importer/compare/3.2.3...3.2.4
[3.2.3]: https://github.com/abdnh/anki-copycat-importer/compare/3.2.2...3.2.3
[3.2.2]: https://github.com/abdnh/anki-copycat-importer/compare/3.2.1...3.2.2
[3.2.1]: https://github.com/abdnh/anki-copycat-importer/compare/3.2.0...3.2.1
[3.2.0]: https://github.com/abdnh/anki-copycat-importer/compare/3.1.5...3.2.0
[3.1.5]: https://github.com/abdnh/anki-copycat-importer/compare/3.1.4...3.1.5
[3.1.4]: https://github.com/abdnh/anki-copycat-importer/compare/3.1.3...3.1.4
[3.1.3]: https://github.com/abdnh/anki-copycat-importer/compare/3.1.2...3.1.3
[3.1.2]: https://github.com/abdnh/anki-copycat-importer/compare/3.1.1...3.1.2
[3.1.1]: https://github.com/abdnh/anki-copycat-importer/compare/3.1.0...3.1.1
[3.1.0]: https://github.com/abdnh/anki-copycat-importer/compare/3.0.5...3.1.0
[3.0.5]: https://github.com/abdnh/anki-copycat-importer/compare/3.0.4...3.0.5
[3.0.4]: https://github.com/abdnh/anki-copycat-importer/compare/3.0.3...3.0.4
[3.0.3]: https://github.com/abdnh/anki-copycat-importer/compare/3.0.2...3.0.3
[3.0.2]: https://github.com/abdnh/anki-copycat-importer/compare/3.0.1...3.0.2
[3.0.1]: https://github.com/abdnh/anki-copycat-importer/compare/3.0.0...3.0.1
[3.0.0]: https://github.com/abdnh/anki-copycat-importer/compare/2.3.1...3.0.0
[2.3.1]: https://github.com/abdnh/anki-copycat-importer/compare/2.3.0...2.3.1
[2.3.0]: https://github.com/abdnh/anki-copycat-importer/compare/2.2.4...2.3.0
[2.2.4]: https://github.com/abdnh/anki-copycat-importer/compare/2.2.3...2.2.4
[2.2.3]: https://github.com/abdnh/anki-copycat-importer/compare/2.2.2...2.2.3
[2.2.2]: https://github.com/abdnh/anki-copycat-importer/compare/2.2.1...2.2.2
[2.2.1]: https://github.com/abdnh/anki-copycat-importer/compare/2.2.0...2.2.1
[2.2.0]: https://github.com/abdnh/anki-copycat-importer/compare/2.1.2...2.2.0
[2.1.2]: https://github.com/abdnh/anki-copycat-importer/compare/2.1.1...2.1.2
[2.1.1]: https://github.com/abdnh/anki-copycat-importer/compare/2.1.0...2.1.1
[2.1.0]: https://github.com/abdnh/anki-copycat-importer/compare/2.0.0...2.1.0
[2.0.0]: https://github.com/abdnh/anki-copycat-importer/compare/1.6.0...2.0.0
[1.6.0]: https://github.com/abdnh/anki-copycat-importer/compare/1.5.8...1.6.0
[1.5.8]: https://github.com/abdnh/anki-copycat-importer/compare/1.5.7...1.5.8
[1.5.7]: https://github.com/abdnh/anki-copycat-importer/compare/1.5.6...1.5.7
[1.5.6]: https://github.com/abdnh/anki-copycat-importer/compare/1.5.5...1.5.6
[1.5.5]: https://github.com/abdnh/anki-copycat-importer/compare/1.5.4...1.5.5
[1.5.4]: https://github.com/abdnh/anki-copycat-importer/compare/1.5.3...1.5.4
[1.5.3]: https://github.com/abdnh/anki-copycat-importer/compare/1.5.2...1.5.3
[1.5.2]: https://github.com/abdnh/anki-copycat-importer/compare/1.5.1...1.5.2
[1.5.1]: https://github.com/abdnh/anki-copycat-importer/compare/1.5.0...1.5.1
[1.5.0]: https://github.com/abdnh/anki-copycat-importer/compare/1.4.1...1.5.0
[1.4.1]: https://github.com/abdnh/anki-copycat-importer/compare/1.4.0...1.4.1
[1.4.0]: https://github.com/abdnh/anki-copycat-importer/compare/1.3.1...1.4.0
[1.3.1]: https://github.com/abdnh/anki-copycat-importer/compare/1.3.0...1.3.1
[1.3.0]: https://github.com/abdnh/anki-copycat-importer/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/abdnh/anki-copycat-importer/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/abdnh/anki-copycat-importer/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/abdnh/anki-copycat-importer/releases/tag/1.0.0
