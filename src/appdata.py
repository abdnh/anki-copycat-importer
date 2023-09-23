import functools
import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple, Union

try:
    from anki.utils import is_mac, is_win
except ImportError:
    from anki.utils import isMac as is_mac  # type: ignore
    from anki.utils import isWin as is_win  # type: ignore


def get_ankiapp_data_folder() -> Optional[str]:
    path = None
    if is_win:
        from aqt.winpaths import get_appdata

        path = os.path.join(get_appdata(), "AnkiApp")
    elif is_mac:
        path = os.path.expanduser("~/Library/Application Support/AnkiApp")
        if not os.path.exists(path):
            # App store verison
            path = os.path.expanduser(
                "~/Library/Containers/com.ankiapp.client/Data/Documents/ankiapp"
            )

    if path is not None and os.path.exists(path):
        return path
    return None


# pylint: disable=too-few-public-methods
class AnkiAppData:
    def __init__(self, path: Union[Path, str]):
        self.path = Path(path)

    @functools.cached_property
    def sqlite_dbs(self) -> List[Path]:
        databases_path = self.path / "databases"
        databases_db_path = databases_path / "Databases.db"
        if not databases_db_path.exists():
            return []
        with sqlite3.connect(databases_db_path) as conn:
            db_paths = []
            for row in conn.execute("select origin from Databases"):
                # Use the first file found in the database subfolder
                # TODO: inevstigate whether this can cause problems
                db_path = next((databases_path / str(row[0])).iterdir(), None)
                if db_path:
                    db_paths.append(db_path)
            return db_paths

    @functools.cached_property
    def indexeddb_dbs(self) -> List[Tuple[Path, Path]]:
        paths: List[Tuple[Path, Path]] = []
        databases_path = self.path / "IndexedDB"
        for leveldb_path in databases_path.glob("*.leveldb"):
            if leveldb_path.is_dir():
                blob_path = leveldb_path.with_suffix(".blob")
                if blob_path.is_dir():
                    paths.append((leveldb_path, blob_path))

        return paths


if __name__ == "__main__":
    appdata = AnkiAppData(get_ankiapp_data_folder())
    print(appdata.sqlite_dbs)
    print(appdata.indexeddb_dbs)
