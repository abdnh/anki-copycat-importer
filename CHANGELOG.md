# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.1] - 2022-12-19

### Fixed

-   Fix issue with AnkiApp templates containing field references that differ in case from how the fields are actually named.

## [1.4.0] - 2022-10-22

### Added

-   Work around media importing not working for newer AnkiApp versions (tested on 6.1.0).
    Importing may take longer to complete, as the add-on now falls back to downloading media directly from AnkiApp's servers in case it can't find them in the local database. See [this forum post](https://forums.ankiweb.net/t/ankiapp-importer/16734/39).

## [1.3.1] - 2022-07-01

### Fixed

-   Fixed AnkiApp database file not being selectable in macOS's file selector.

### Added

-   Added a note about empty collections.

## [1.3.0] - 2022-04-15

### Added

-   Handle missing media files and warn about them.

## [1.2.0] - 2022-03-05

### Added

-   Show progress dialog and the number of imported notes.

### Fixed

-   Fix for some image formats not being recognized.
-   Fix import error on some collections with missing field names in the `layouts` table.

## [1.1.0] - 2022-01-21

### Added

-   Deck description is now imported.

## [1.0.0] - 2022-01-17

Initial release

[1.4.1]: https://github.com/abdnh/AnkiApp-importer/compare/1.4.0...1.4.1
[1.4.0]: https://github.com/abdnh/AnkiApp-importer/compare/1.3.1...1.4.0
[1.3.1]: https://github.com/abdnh/AnkiApp-importer/compare/1.3.0...1.3.1
[1.3.0]: https://github.com/abdnh/AnkiApp-importer/compare/1.2.0...1.3.0
[1.2.0]: https://github.com/abdnh/AnkiApp-importer/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/abdnh/AnkiApp-importer/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/abdnh/AnkiApp-importer/releases/tag/1.0.0
