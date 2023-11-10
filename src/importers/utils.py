import html
import mimetypes
import urllib

import aqt

from .errors import CopycatImporterError

# https://github.com/ankitects/anki/blob/a58b2a986ceebbf7d5d863dfa5acf206b0c2ab02/qt/aqt/editor.py#L836


def fname_to_link(fname: str) -> str:
    ext = fname.split(".")[-1].lower()
    if ext in aqt.editor.pics:
        name = urllib.parse.quote(fname.encode("utf8"))
        return f'<img src="{name}">'
    return f"[sound:{html.escape(fname, quote=False)}]"


def guess_extension(mime: str) -> str:
    # Work around guess_extension() not recognizing some file types
    extensions_for_mimes = {
        # .webp is not recognized on Windows without additional software
        # (https://storage.googleapis.com/downloads.webmproject.org/releases/webp/WebpCodecSetup.exe)
        "image/webp": ".webp",
        "image/jp2": ".jp2",
        "audio/mp3": ".mp3",
    }

    ext = mimetypes.guess_extension(mime)
    if not ext:
        try:
            ext = extensions_for_mimes[mime]
        except KeyError as exc:
            raise CopycatImporterError(f"unrecognized media type: {mime}") from exc

    return ext


def guess_mime(data: bytes) -> str:
    from_buffer = None
    try:
        import magic

        from_buffer = magic.from_buffer
    except ImportError:
        import puremagic

        from_buffer = puremagic.from_string

    return from_buffer(data, mime=True)
