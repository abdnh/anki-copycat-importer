import html
import mimetypes
import urllib
from typing import Optional

import aqt

# https://github.com/ankitects/anki/blob/a58b2a986ceebbf7d5d863dfa5acf206b0c2ab02/qt/aqt/editor.py#L836


def fname_to_link(fname: str) -> str:
    ext = fname.split(".")[-1].lower()
    if ext in aqt.editor.pics:
        name = urllib.parse.quote(fname.encode("utf8"))
        return f'<img src="{name}">'
    return f"[sound:{html.escape(fname, quote=False)}]"


def guess_extension(mime: str) -> Optional[str]:
    # Work around guess_extension() not recognizing some file types
    extensions_for_mimes = {
        # .webp is not recognized on Windows without additional software
        # (https://storage.googleapis.com/downloads.webmproject.org/releases/webp/WebpCodecSetup.exe)
        "image/webp": ".webp",
        "image/jp2": ".jp2",
        "audio/mp3": ".mp3",
        "audio/x-m4a": ".m4a",
    }

    ext = mimetypes.guess_extension(mime)
    if not ext:
        try:
            ext = extensions_for_mimes[mime]
        except KeyError:
            return None

    return ext
