from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from pytest import MonkeyPatch

if TYPE_CHECKING:
    from src.importers.ankiapp import AnkiAppImporter

from .fixtures import MockMainWindow

if TYPE_CHECKING:
    from aqt.main import AnkiQt

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def mw(monkeypatch: MonkeyPatch) -> AnkiQt:
    col_dir = tempfile.mkdtemp()
    mock = cast("AnkiQt", MockMainWindow(os.path.join(col_dir, "collection.anki2")))
    import aqt

    monkeypatch.setattr(aqt, "mw", mock)
    return mock


@pytest.fixture
def simple_importer(mw: AnkiQt) -> AnkiAppImporter:
    from src.importers.ankiapp import (
        AnkiAppImporter,
        ImportedPathInfo,
        ImportedPathType,
    )

    paths = [ImportedPathInfo(DATA_DIR / "simple.db", ImportedPathType.DB_PATH)]
    return AnkiAppImporter(mw, paths)


def test_simple(simple_importer: AnkiAppImporter) -> None:
    assert len(simple_importer.notetypes) == 1
    notetype = next(iter(simple_importer.notetypes.values()))
    assert set(notetype.fields) == {"Front", "Back"}
    assert len(simple_importer.decks) == 1
    deck = next(iter(simple_importer.decks.values()))
    assert deck.name == "basic deck"
    assert deck.description == "my basic deck"
    assert len(simple_importer.cards) == 1
    card = next(iter(simple_importer.cards.values()))
    assert card.fields["Front"] == "front text"
    assert card.fields["Back"] == "back text"
    assert card.tags == ["mytag"]
