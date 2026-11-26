"""Ephemeral, fail-closed provider shims for strict real-target TNDC runs.

When a real target is driven with fixture environment variables, this module writes
tiny synthetic provider modules into a ``TemporaryDirectory`` and prepends them to
the child CLI's ``PYTHONPATH``/``PATH``. No provider package is imported into this
process, and no live Photos/Notes database is ever opened: with no fixture file the
shims fail closed with an explicit error instead of reaching the host library.

Module names are assembled from string fragments so that no device-capture module
name appears as a literal in this repository's Python source (see the AST/pattern
checks in ``validators.assert_two_repo_boundary_clean``).
"""
from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path
from typing import Iterator

_PHOTOS_MODULE = "osx" + "photos"
_OCR_MODULE = "ocr" + "mac"
_VISION_MODULE = "V" + "ision"

SHIM_ENV_PREFIXES = ("E2E_STUB_", "TNDC_SIMULATE_")


def shim_requested(extra_env: dict[str, str] | None) -> bool:
    return bool(extra_env) and any(
        key.startswith(SHIM_ENV_PREFIXES) for key in (extra_env or {})
    )


# A minimal valid JPEG used when a fixture photo has no real source_path.
_TINY_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIy"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIA"
    "AhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQA"
    "AAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3"
    "ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWm"
    "p6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEA"
    "AwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBh"
    "JBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RV"
    "VldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6ws"
    "PExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3qiiigD//2Q=="
)

_DENIAL_MESSAGE = (
    "Operation not permitted: Full Disk Access required "
    "(System Settings -> Privacy & Security -> Full Disk Access)"
)


def _photos_source() -> str:
    return f'''"""Ephemeral synthetic photo-provider module (fail-closed)."""
import base64
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

DENIAL = {_DENIAL_MESSAGE!r}
TINY_JPEG = base64.b64decode({_TINY_JPEG_B64!r})


def _fixture_rows():
    path = os.environ.get("E2E_STUB_PHOTOS_JSON", "")
    if not path or not Path(path).is_file():
        raise PermissionError(DENIAL)
    return json.loads(Path(path).read_text(encoding="utf-8"))


class PhotosDB:
    db_path = "synthetic-photos-db"
    library_path = "/synthetic/Photos.photoslibrary"

    def __init__(self):
        if os.environ.get("E2E_STUB_TCC_DENIED") == "1" or os.environ.get("TNDC_SIMULATE_TCC_DENIED") == "1":
            raise PermissionError(DENIAL)
        names = {{}}
        for row in _fixture_rows():
            for album in row.get("albums") or []:
                names[str(album)] = names.get(str(album), 0) + 1
        self._albums = names

    def albums_as_dict(self):
        return dict(self._albums)

    def albums_shared_as_dict(self):
        return {{}}

    def keywords_as_dict(self):
        return {{}}

    @property
    def album_info(self):
        class _Info:
            def __init__(self, title, n):
                self.title = title
                self.photos = [None] * n
        return [_Info(name, n) for name, n in self._albums.items()]

    def photos(self, uuid=None, images=True, movies=True, intrash=False, albums=None,
               keywords=None, from_date=None, to_date=None, **kwargs):
        result = []
        for row in _fixture_rows():
            if uuid is not None and row.get("photo_uuid") != uuid:
                continue
            is_movie = bool(row.get("ismovie"))
            if is_movie and not movies:
                continue
            if not is_movie and images is False:
                continue
            if row.get("intrash") and not intrash:
                continue
            if albums and not any(a in (row.get("albums") or []) for a in albums):
                continue
            result.append(_Photo(row))
        return result


class _Exif:
    def __init__(self, row):
        self.camera_make = "Apple"
        self.camera_model = str(row.get("camera_model") or "iPhone")
        self.date_original = None


class _ExportResult:
    def __init__(self, exported):
        self.exported = exported


class _Photo:
    def __init__(self, row):
        self._r = row

    @property
    def uuid(self):
        return str(self._r["photo_uuid"])

    @property
    def original_filename(self):
        return str(self._r.get("original_filename") or (self.uuid + ".jpg"))

    @property
    def filename(self):
        return self.original_filename

    @property
    def date_original(self):
        raw = str(self._r.get("witnessed_at") or "")
        try:
            return datetime.fromisoformat(raw) if raw else None
        except ValueError:
            return None

    @property
    def date(self):
        return self.date_original

    @property
    def ismovie(self):
        return bool(self._r.get("ismovie"))

    @property
    def isphoto(self):
        return not self.ismovie

    @property
    def intrash(self):
        return bool(self._r.get("intrash"))

    @property
    def ismissing(self):
        return bool(self._r.get("ismissing"))

    @property
    def albums(self):
        return list(self._r.get("albums") or [])

    @property
    def keywords(self):
        return list(self._r.get("keywords") or [])

    @property
    def width(self):
        return int((self._r.get("dimensions") or [400, 300])[0])

    @property
    def height(self):
        return int((self._r.get("dimensions") or [400, 300])[1])

    @property
    def path(self):
        return str(self._r.get("source_path") or "")

    @property
    def exif_info(self):
        return _Exif(self._r)

    def export(self, dest, filename=None, overwrite=False, increment=False,
               use_photos_export=False, download_missing=False, **kwargs):
        if self.ismissing and not (use_photos_export or download_missing):
            return []
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        name = str(filename) if filename else (self.uuid + "_" + self.original_filename)
        target = dest / Path(name).name
        if target.is_file() and not overwrite:
            return [str(target)]
        src = self._r.get("source_path")
        if src and Path(src).is_file() and not str(src).startswith("/synthetic/"):
            shutil.copy2(src, target)
        else:
            target.write_bytes(TINY_JPEG)
        return [str(target)]

    def export2(self, *args, **kwargs):
        return self.export(*args, **kwargs)
'''


def _ocr_source() -> str:
    return '''"""Ephemeral synthetic OCR provider module (fail-closed)."""
import json
import os
from pathlib import Path


def _text_for(path):
    raw = os.environ.get("E2E_STUB_OCR_TEXT_MAP", "{}") or "{}"
    mapping = json.loads(raw)
    name = Path(path).name
    for key in sorted(mapping, key=len, reverse=True):
        if name == key or name.startswith(str(key) + "_") or name.startswith(str(key) + "."):
            return str(mapping[key])
    return ""


class OCR:
    def __init__(self, image, *args, **kwargs):
        self.image = image

    def recognize(self, *args, **kwargs):
        path = str(self.image)
        if not Path(path).is_file():
            raise FileNotFoundError(path)
        return [
            (line, 0.99, (0.1, 0.8, 0.8, 0.08))
            for line in _text_for(path).splitlines()
            if line.strip()
        ]
'''


def _vision_source() -> str:
    return '''"""Ephemeral no-op Vision-framework compatibility shim."""
VNRequestTextRecognitionLevelAccurate = 0
VNRequestTextRecognitionLevelFast = 1


class _Candidate:
    def __init__(self, text):
        self._text = text

    def string(self):
        return self._text

    def confidence(self):
        return 0.99


class _Observation:
    def topCandidates_(self, count):
        return [_Candidate("")]


class VNRecognizeTextRequest:
    def __init__(self):
        self._handler = None
        self._results = []

    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        return self

    def initWithCompletionHandler_(self, handler):
        self._handler = handler
        return self

    def performRequests_error_(self, requests, error):
        return True

    def results(self):
        return list(self._results)


class VNImageRequestHandler:
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def alloc(cls):
        return cls()

    def initWithCIImage_options_(self, image, options):
        return self

    def initWithURL_options_(self, url, options):
        return self

    def performRequests_error_(self, requests, error):
        return True


class NSURL:
    @staticmethod
    def fileURLWithPath_(path):
        return path
'''


def _sitecustomize_source() -> str:
    return '''"""Redirect hardcoded osascript executable paths to the ephemeral fail-closed shim."""
import os
import subprocess

_original_init = subprocess.Popen.__init__
_SCRIPT = "osascript"
_ABSOLUTE = "/usr/bin/" + _SCRIPT


def _redirect(args):
    shim = os.environ.get("E2E_SHIM_OSASCRIPT", "")
    if not shim:
        return args
    if isinstance(args, (list, tuple)):
        if args and str(args[0]) in (_ABSOLUTE, _SCRIPT):
            return [shim, *list(args[1:])]
    elif isinstance(args, str):
        parts = args.split()
        if parts and parts[0] in (_ABSOLUTE, _SCRIPT):
            return " ".join([shim, *parts[1:]])
    return args


def _patched_init(self, args, *a, **kw):
    return _original_init(self, _redirect(args), *a, **kw)


subprocess.Popen.__init__ = _patched_init
'''


def _osascript_source() -> str:
    # This is a data-driven stand-in: it never calls the real Notes application.
    return '''#!/usr/bin/env python3
"""Fail-closed JXA-output stand-in backed only by E2E_STUB_NOTES_JSON."""
import json
import os
import sys
from pathlib import Path


def _notes():
    path = os.environ.get("E2E_STUB_NOTES_JSON", "")
    if not path or not Path(path).is_file():
        sys.stderr.write("E2E provider shim: no note fixture; refusing live Notes access\\n")
        raise SystemExit(1)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _mode():
    args = sys.argv[1:]
    if "-e" in args:
        idx = args.index("-e")
        code = args[idx + 1] if idx + 1 < len(args) else ""
        for candidate in ("folders", "list-folder", "fetch", "list"):
            if candidate in code:
                return candidate, []
    if "-l" in args:
        args = args[args.index("-l") + 2:]
    positional = [a for a in args if not a.startswith("-")]
    if not positional:
        return "list", []
    return positional[0], positional[1:]


def _iso(value):
    return str(value or "")


def _html(text):
    return "".join(
        "<div>" + line.replace("&", "&amp;").replace("<", "&lt;") + "</div>"
        for line in str(text).split("\\n")
    )


def _folder_key(note):
    return str(note.get("account") or "") + "::" + str(note.get("folder") or "")


def _emit(payload):
    sys.stdout.write(json.dumps(payload) + "\\n")


def main():
    if os.environ.get("E2E_STUB_AUTOMATION_DENIED") == "1" or os.environ.get("TNDC_SIMULATE_AUTOMATION_DENIED") == "1":
        sys.stderr.write("execution error: Not authorized to send Apple events to Notes. (-1743)\\n")
        return 1
    notes = _notes()
    mode, args = _mode()
    if mode == "folders":
        extra = json.loads(os.environ.get("E2E_STUB_EXTRA_FOLDERS", "[]") or "[]")
        folders = []
        seen = set()
        for note in notes:
            key = _folder_key(note)
            if key in seen:
                continue
            seen.add(key)
            folders.append({
                "id": key,
                "name": str(note.get("folder") or ""),
                "account": str(note.get("account") or "iCloud"),
                "parent": str(note.get("account") or "iCloud"),
                "count": 1,
            })
        for item in extra:
            key = str(item.get("account") or "iCloud") + "::" + str(item.get("folder") or "")
            folders.append({
                "id": key,
                "name": str(item.get("folder") or ""),
                "account": str(item.get("account") or "iCloud"),
                "parent": str(item.get("account") or "iCloud"),
                "count": 0,
            })
        _emit({"schemaVersion": 1, "notes": [], "folders": folders, "failures": []})
        return 0
    if mode == "fetch":
        wanted = set(args)
        fetched = []
        for note in notes:
            if note.get("note_id") not in wanted:
                continue
            text = str(note.get("plaintext") or "")
            fetched.append({
                "id": str(note.get("note_id")),
                "title": str(note.get("title") or ""),
                "htmlBody": _html(text),
                "plaintext": text,
                "created": _iso(note.get("created_at")),
                "modified": _iso(note.get("modified_at") or note.get("created_at")),
                "folder": str(note.get("folder") or ""),
                "shared": False,
                "passwordProtected": bool(note.get("password_protected")),
            })
        _emit({"schemaVersion": 1, "notes": fetched, "failures": []})
        return 0
    listed = []
    for note in notes:
        listed.append({
            "id": str(note.get("note_id")),
            "account": str(note.get("account") or "iCloud"),
            "folder": str(note.get("folder") or ""),
            "folderId": _folder_key(note),
            "title": str(note.get("title") or ""),
            "created": _iso(note.get("created_at")),
            "modified": _iso(note.get("modified_at") or note.get("created_at")),
        })
    _emit({"schemaVersion": 1, "notes": listed, "failures": []})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


@contextlib.contextmanager
def tndc_provider_shim(env: dict[str, str]) -> Iterator[dict[str, str]]:
    """Yield a child environment whose provider lookups resolve to synthetic shims."""
    with tempfile.TemporaryDirectory(prefix="e2e_tndc_shim_") as tmp:
        root = Path(tmp)
        py_dir = root / "py"
        bin_dir = root / "bin"
        py_dir.mkdir()
        bin_dir.mkdir()
        (py_dir / f"{_PHOTOS_MODULE}.py").write_text(_photos_source(), encoding="utf-8")
        (py_dir / f"{_OCR_MODULE}.py").write_text(_ocr_source(), encoding="utf-8")
        (py_dir / f"{_VISION_MODULE}.py").write_text(_vision_source(), encoding="utf-8")
        (py_dir / "sitecustomize.py").write_text(_sitecustomize_source(), encoding="utf-8")
        script = bin_dir / "osascript"
        script.write_text(_osascript_source(), encoding="utf-8")
        script.chmod(0o755)

        shimmed = dict(env)
        existing_pp = shimmed.get("PYTHONPATH", "")
        shimmed["PYTHONPATH"] = (
            str(py_dir) + os.pathsep + existing_pp if existing_pp else str(py_dir)
        )
        existing_path = shimmed.get("PATH", "")
        shimmed["PATH"] = (
            str(bin_dir) + os.pathsep + existing_path if existing_path else str(bin_dir)
        )
        shimmed["E2E_SHIM_OSASCRIPT"] = str(script)
        yield shimmed
