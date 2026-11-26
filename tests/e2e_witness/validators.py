"""Validators for JPEG metadata, privacy hygiene, Two-Clock Rule, schemas, and boundaries."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
import struct
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

from .fixtures import CorpusIndex

FORBIDDEN_PUBLIC_KEYS = {
    "plaintext",
    "local_path",
    "ocr_text",
    "raw_ocr",
    "htmlBody",
    "html_body",
    "body",
    "title",
    "folder",
}

FORBIDDEN_JPEG_MARKERS = {
    0xFFE1: "APP1 (EXIF/XMP)",
    0xFFE2: "APP2 (ICC/FPXR)",
    0xFFED: "APP13 (IPTC/Photoshop)",
    0xFFFE: "COM (JPEG Comment)",
}

FORBIDDEN_JPEG_SUBSTRINGS = (
    b"Exif\x00\x00",
    b"http://ns.adobe.com/xap/1.0/",
    b"ICC_PROFILE",
    b"GPSLatitude",
    b"DateTimeOriginal",
    b"Photoshop 3.0",
)

FORBIDDEN_JHW_IMPORTS = {"osxphotos", "ocrmac", "Vision", "pyobjc"}
FORBIDDEN_JHW_PATTERNS = (
    "Photos.sqlite",
    "NoteStore.sqlite",
    'Application("Notes")',
    "Application('Notes')",
)

ISO_TZ_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_jpeg_segments(data: bytes) -> list[tuple[int, bytes]]:
    """Walk JPEG marker stream from SOI (0xFFD8) to SOS (0xFFDA)."""
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        raise AssertionError("Invalid JPEG: missing SOI marker (0xFFD8)")
    segments: list[tuple[int, bytes]] = []
    pos = 2
    n = len(data)
    while pos < n:
        while pos < n and data[pos] == 0xFF:
            pos += 1
        if pos >= n:
            break
        marker = 0xFF00 | data[pos]
        pos += 1
        if marker == 0xFFD9:  # EOI
            segments.append((marker, b""))
            break
        if marker == 0xFF00 or (0xFFD0 <= marker <= 0xFFD7) or marker == 0xFF01:
            continue
        if pos + 2 > n:
            raise AssertionError(f"Truncated JPEG segment at offset {pos} for marker {marker:#06x}")
        seg_len = struct.unpack(">H", data[pos : pos + 2])[0]
        if seg_len < 2 or pos + seg_len > n:
            raise AssertionError(f"Invalid JPEG segment length {seg_len} for {marker:#06x}")
        payload = data[pos + 2 : pos + seg_len]
        segments.append((marker, payload))
        pos += seg_len
        if marker == 0xFFDA:  # SOS: image scan entropy follows
            break
    return segments


def assert_jpeg_metadata_clean(jpeg_path: Path) -> None:
    """Dual-layer check: byte-level JPEG segment parser + Pillow metadata inspection."""
    if not jpeg_path.is_file():
        raise AssertionError(f"Exported JPEG missing: {jpeg_path}")
    raw = jpeg_path.read_bytes()
    segments = parse_jpeg_segments(raw)

    for marker, payload in segments:
        if marker in FORBIDDEN_JPEG_MARKERS:
            raise AssertionError(
                f"Forbidden JPEG metadata segment {FORBIDDEN_JPEG_MARKERS[marker]} "
                f"({marker:#06x}, {len(payload)}B) in {jpeg_path.name}"
            )
        if b"\xff\xd8" in payload:
            raise AssertionError(f"Embedded nested JPEG SOI thumbnail found in {jpeg_path.name}")

    for needle in FORBIDDEN_JPEG_SUBSTRINGS:
        if needle in raw:
            raise AssertionError(
                f"Forbidden metadata signature {needle!r} found in {jpeg_path.name}"
            )

    # Layer 2: Pillow verification
    with Image.open(jpeg_path) as img:
        img.verify()
    with Image.open(jpeg_path) as img2:
        img2.load()
        if img2.width <= 0 or img2.height <= 0:
            raise AssertionError(f"Invalid image dimensions in {jpeg_path.name}")
        exif = img2.getexif()
        if len(exif) > 0:
            raise AssertionError(f"Pillow getexif() non-empty ({dict(exif)}) in {jpeg_path.name}")
        for ifd_id in (0x8769, 0x8825, -1):
            try:
                sub = exif.get_ifd(ifd_id)
                if sub:
                    raise AssertionError(
                        f"Pillow IFD {ifd_id:#x} non-empty in {jpeg_path.name}"
                    )
            except KeyError:
                pass
        for bad_info in ("exif", "xmp", "icc_profile", "photoshop", "iptc", "comment", "applist"):
            if img2.info.get(bad_info):
                raise AssertionError(
                    f"Pillow info[{bad_info!r}] non-empty in {jpeg_path.name}"
                )


def assert_public_privacy_clean(
    data: Any,
    forbidden_substrings: list[str] | tuple[str, ...] = (),
    context: str = "public_artifact",
) -> None:
    """Recursively verify zero private keys, local paths, or forbidden substrings exist."""

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in FORBIDDEN_PUBLIC_KEYS:
                    raise AssertionError(
                        f"[{context}] Forbidden private key {k!r} at {path}.{k}"
                    )
                _walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                _walk(item, f"{path}[{idx}]")
        elif isinstance(node, str):
            if "/Users/" in node or "/Volumes/Archive4T/Media/intake" in node or "file://" in node:
                raise AssertionError(
                    f"[{context}] Private local path leaked at {path}: {node!r}"
                )
            for sub in forbidden_substrings:
                if sub and sub in node:
                    raise AssertionError(
                        f"[{context}] Forbidden private substring {sub!r} leaked at {path}"
                    )

    _walk(data, "$")


def assert_two_clock_clean(
    chronology: dict[str, Any],
    digitized_at: str = "2015-09",
    confirmed_photo_dates: set[str] | None = None,
) -> None:
    """Verify codex_scan.digitized_at never leaks into est_start/est_end/amalgamated_sort_key."""
    confirmed_photo_dates = confirmed_photo_dates or set()
    dig_prefix = digitized_at[:7]
    for entry in chronology.get("physical_codex_order", []):
        pid = entry.get("piece_id")
        codex_scan = entry.get("witnesses", {}).get("codex_scan", {})
        if codex_scan.get("digitized_at") != digitized_at:
            raise AssertionError(
                f"{pid}: codex_scan.digitized_at expected {digitized_at!r}, "
                f"got {codex_scan.get('digitized_at')!r}"
            )
        chron = entry.get("chronology", {})
        for field in ("est_start", "est_end"):
            val = chron.get(field)
            if isinstance(val, str) and val.startswith(dig_prefix) and val[:10] not in confirmed_photo_dates:
                raise AssertionError(
                    f"{pid}: Two-Clock breach — {field}={val!r} uses digitized_at {digitized_at!r}"
                )
        sort_key = chron.get("amalgamated_sort_key")
        if (
            isinstance(sort_key, str)
            and sort_key.startswith(dig_prefix)
            and sort_key[:10] not in confirmed_photo_dates
        ):
            raise AssertionError(
                f"{pid}: Two-Clock breach — amalgamated_sort_key={sort_key!r} uses digitized_at"
            )


def assert_two_clock_invariant(chron_a: dict[str, Any], chron_b: dict[str, Any]) -> None:
    """Changing --digitized-at across decades must leave all composition dates identical."""
    pieces_a = {e["piece_id"]: e for e in chron_a["physical_codex_order"]}
    pieces_b = {e["piece_id"]: e for e in chron_b["physical_codex_order"]}
    if set(pieces_a) != set(pieces_b):
        raise AssertionError("Piece IDs differ between Two-Clock invariance runs")
    for pid, ea in pieces_a.items():
        eb = pieces_b[pid]
        if ea["chronology"] != eb["chronology"]:
            raise AssertionError(
                f"Two-Clock invariance violated on {pid}: "
                f"{ea['chronology']} vs {eb['chronology']}"
            )


def assert_mode_0600(path: Path) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o600:
        raise AssertionError(f"Expected 0o600 permissions on {path}, got {oct(mode)}")


def assert_mode_0700(path: Path) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o700:
        raise AssertionError(f"Expected 0o700 permissions on {path}, got {oct(mode)}")


def validate_photo_witnesses_schema(data: Any) -> None:
    if not isinstance(data, list):
        raise AssertionError("photo_witnesses.json must be a JSON array")
    required = {
        "photo_uuid",
        "original_filename",
        "local_path",
        "photo_sha256",
        "witnessed_at",
        "camera_model",
        "dimensions",
        "albums",
        "keywords",
        "is_in_icloud_only",
    }
    prev_ts = ""
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise AssertionError(f"photo_witnesses[{idx}] must be an object")
        missing = required - set(item.keys())
        if missing:
            raise AssertionError(f"photo_witnesses[{idx}] missing keys: {sorted(missing)}")
        if not str(item["photo_sha256"]).startswith("sha256:"):
            raise AssertionError(f"photo_witnesses[{idx}] invalid photo_sha256")
        ts = str(item["witnessed_at"])
        if not ISO_TZ_RE.match(ts):
            raise AssertionError(f"photo_witnesses[{idx}] witnessed_at lacks ISO8601+tz: {ts!r}")
        if ts < prev_ts:
            raise AssertionError(
                f"photo_witnesses not sorted ascending by witnessed_at at [{idx}]: {ts} < {prev_ts}"
            )
        prev_ts = ts


def validate_ios_notes_schema(data: Any) -> None:
    if not isinstance(data, list):
        raise AssertionError("ios_notes.json must be a JSON array")
    required = {
        "note_id",
        "folder",
        "title",
        "created_at",
        "modified_at",
        "plaintext",
        "text_sha256",
    }
    prev_ts = ""
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise AssertionError(f"ios_notes[{idx}] must be an object")
        missing = required - set(item.keys())
        if missing:
            raise AssertionError(f"ios_notes[{idx}] missing keys: {sorted(missing)}")
        if not str(item["text_sha256"]).startswith("sha256:"):
            raise AssertionError(f"ios_notes[{idx}] invalid text_sha256")
        ts = str(item["created_at"])
        if ts < prev_ts:
            raise AssertionError(
                f"ios_notes not sorted ascending by created_at at [{idx}]: {ts} < {prev_ts}"
            )
        prev_ts = ts


def validate_ocr_cache_schema(data: Any) -> None:
    if not isinstance(data, dict):
        raise AssertionError("ocr_cache.json must be a JSON object keyed by photo_uuid")
    for uuid, entry in data.items():
        if not isinstance(entry, dict):
            raise AssertionError(f"ocr_cache[{uuid!r}] must be an object")
        for key in ("text", "lines", "ocr_engine", "ocr_at"):
            if key not in entry:
                raise AssertionError(f"ocr_cache[{uuid!r}] missing key {key!r}")
        if not isinstance(entry["text"], str) or not isinstance(entry["lines"], list):
            raise AssertionError(f"ocr_cache[{uuid!r}] invalid types for text/lines")


def validate_witness_links_schema(data: Any) -> None:
    if not isinstance(data, dict):
        raise AssertionError("witness_links.json must be a JSON object")
    for key in ("schema", "generated_at", "intake_summary", "photo_links", "note_links"):
        if key not in data:
            raise AssertionError(f"witness_links.json missing top-level key {key!r}")
    if data["schema"] != "versforms.witness-links.v1":
        raise AssertionError(f"Unexpected witness_links schema: {data['schema']!r}")
    for p in data["photo_links"]:
        if len(p.get("candidates", [])) > 3:
            raise AssertionError(f"Photo {p.get('photo_uuid')} has >3 candidates")
        if p.get("status") not in {"pending_review", "confirmed", "rejected"}:
            raise AssertionError(f"Invalid photo status: {p.get('status')!r}")
        if p.get("textual_state") not in {
            "unreviewed",
            "matches_scan",
            "predates_scan_edits",
            "partial_page",
        }:
            raise AssertionError(f"Invalid textual_state: {p.get('textual_state')!r}")
    for n in data["note_links"]:
        if len(n.get("candidates", [])) > 3:
            raise AssertionError(f"Note {n.get('note_id')} has >3 candidates")
        if n.get("status") not in {"pending_review", "confirmed", "rejected"}:
            raise AssertionError(f"Invalid note status: {n.get('status')!r}")
        if n.get("relation") not in {
            "unreviewed",
            "standalone_cohort",
            "source_fragment",
            "parallel_draft",
        }:
            raise AssertionError(f"Invalid note relation: {n.get('relation')!r}")


def validate_chronology_schema(
    data: Any,
    corpus: CorpusIndex,
    links_data: dict[str, Any] | None = None,
) -> None:
    if not isinstance(data, dict):
        raise AssertionError("chronology.json must be a JSON object")
    for key in (
        "schema",
        "generated_at",
        "digitized_at",
        "physical_codex_order",
        "amalgamated_chronological_order",
    ):
        if key not in data:
            raise AssertionError(f"chronology.json missing key {key!r}")
    if data["schema"] != "versforms.chronology.v1":
        raise AssertionError(f"Unexpected chronology schema: {data['schema']!r}")

    codex = data["physical_codex_order"]
    if len(codex) != 126:
        raise AssertionError(f"Expected 126 pieces in physical_codex_order, got {len(codex)}")

    unconfirmed_uuids: set[str] = set()
    unconfirmed_note_ids: set[str] = set()
    if links_data is not None:
        unconfirmed_uuids = {
            p["photo_uuid"]
            for p in links_data.get("photo_links", [])
            if p.get("status") != "confirmed"
        }
        unconfirmed_note_ids = {
            n["note_id"]
            for n in links_data.get("note_links", [])
            if n.get("status") != "confirmed"
        }

    valid_bases = {
        "photo_anchored",
        "interpolated",
        "extrapolated_head",
        "extrapolated_tail",
        "undated",
    }
    seen_ids: list[str] = []
    for entry in codex:
        pid = entry["piece_id"]
        seen_ids.append(pid)
        witnesses = entry["witnesses"]
        scan = witnesses["codex_scan"]
        surf = scan["surface_id"]
        expected_sha = corpus.canonical_masters.get(surf)
        if expected_sha and scan["scan_sha256"] != expected_sha:
            raise AssertionError(
                f"{pid}: scan_sha256 {scan['scan_sha256']} != canonical {expected_sha}"
            )
        expected_shared = surf in corpus.multi_piece_pages
        if scan["shared_surface"] != expected_shared:
            raise AssertionError(
                f"{pid} ({surf}): shared_surface={scan['shared_surface']}, expected {expected_shared}"
            )
        for pw in witnesses.get("photo_witnesses", []):
            if pw.get("status") in {"pending_review", "rejected"}:
                raise AssertionError(f"{pid}: non-confirmed photo status in chronology: {pw}")
            if pw.get("photo_uuid") in unconfirmed_uuids:
                raise AssertionError(f"{pid}: unconfirmed photo {pw['photo_uuid']} leaked")
        for ln in witnesses.get("linked_ios_notes", []):
            if ln.get("status") in {"pending_review", "rejected"}:
                raise AssertionError(f"{pid}: non-confirmed note status in chronology: {ln}")
            if ln.get("note_id") in unconfirmed_note_ids:
                raise AssertionError(f"{pid}: unconfirmed note {ln['note_id']} leaked")

        chron = entry["chronology"]
        if chron["date_basis"] not in valid_bases:
            raise AssertionError(f"{pid}: invalid date_basis {chron['date_basis']!r}")
        for req_c in ("date_basis", "est_start", "est_end", "anchor_prev", "anchor_next", "amalgamated_sort_key"):
            if req_c not in chron:
                raise AssertionError(f"{pid}: chronology missing {req_c!r}")

    if set(seen_ids) != {f"p{i:03d}" for i in range(1, 127)}:
        raise AssertionError("physical_codex_order does not cover p001..p126")

    amalg = data["amalgamated_chronological_order"]
    if not isinstance(amalg, list) or len(amalg) < 126:
        raise AssertionError("amalgamated_chronological_order must include all pieces + notes")
    sort_keys = [str(item.get("sort_key") or item.get("amalgamated_sort_key") or "") for item in amalg]
    non_empty = [k for k in sort_keys if k and not k.startswith("undated#")]
    if non_empty != sorted(non_empty):
        raise AssertionError("amalgamated_chronological_order dated entries are not sorted ascending")


def _boxes_overlap(
    a: tuple[int, int, int, int],
    b: tuple[int, int, int, int],
) -> bool:
    """True when two half-open [x0, y0, x1, y1] boxes share a positive-area region."""
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def assert_shared_surface_isolated(
    manifest: dict[str, Any],
    out_dir: Path,
    corpus: CorpusIndex,
) -> None:
    """Verify co-tenanted & spread-exposed exports never leak neighbor pieces or spreads.

    Checks manifest crop geometry, actual on-disk JPEG pixel dimensions (so a
    spoofed small ``crop_box`` cannot hide an uncropped full-page export), and
    geometric non-overlap against every co-tenant's raw ink bounds.
    """
    for exp in manifest.get("exports", []):
        pid = exp["piece_id"]
        surf = exp["surface_id"]
        out_file = exp.get("output_file")
        if not out_file:
            raise AssertionError(f"Missing output_file for exported piece {pid} on {surf}")
        img_path = out_dir / out_file
        assert_jpeg_metadata_clean(img_path)
        if "site/img/s/" in str(out_file) or str(out_file).startswith("s/"):
            raise AssertionError(f"Spread image leaked as output: {out_file}")

        crop_box = exp.get("crop_box")
        if not crop_box or len(crop_box) != 4:
            raise AssertionError(f"Missing crop_box for export {pid} on {surf}")
        try:
            crop = tuple(int(v) for v in crop_box)
        except (TypeError, ValueError) as exc:
            raise AssertionError(f"Non-integer crop_box for {pid} on {surf}: {crop_box!r}") from exc

        page = corpus.page_by_id.get(surf)
        if page is None:
            raise AssertionError(f"Unknown surface_id {surf!r} in projection manifest")
        iw, ih = int(page["iw"]), int(page["ih"])
        x0, y0, x1, y1 = crop
        if not (0 <= x0 < x1 <= iw and 0 <= y0 < y1 <= ih):
            raise AssertionError(f"crop_box {crop_box} out of page bounds for {pid} on {surf}")
        w, h = x1 - x0, y1 - y0

        with Image.open(img_path) as im:
            disk_size = im.size
        if disk_size != (w, h):
            raise AssertionError(
                f"On-disk JPEG size {disk_size} does not match crop_box {crop_box} "
                f"for {pid} on {surf}"
            )
        declared = exp.get("dimensions")
        if declared is not None and list(declared) != list(disk_size):
            raise AssertionError(
                f"Manifest dimensions {declared} disagree with disk JPEG {disk_size} "
                f"for {pid} on {surf}"
            )

        if surf not in corpus.multi_piece_pages:
            continue

        if not exp.get("isolated_crop"):
            raise AssertionError(
                f"Co-tenanted page {surf} exported for {pid} without isolated_crop=True"
            )
        if w >= iw - 4 and h >= ih - 4:
            raise AssertionError(
                f"Co-tenanted crop on {surf} for {pid} covers (nearly) the entire page: {crop_box}"
            )
        if disk_size[0] >= iw or disk_size[1] >= ih:
            raise AssertionError(
                f"Co-tenanted export for {pid} on {surf} is not smaller than page: {disk_size}"
            )

        own_raw = corpus.piece_block_bbox(pid, surf, pad=0)
        for other_pid in corpus.multi_piece_pages[surf]:
            if other_pid == pid:
                continue
            other_raw = corpus.piece_block_bbox(other_pid, surf, pad=0)
            if own_raw is not None and other_raw is not None:
                if not _boxes_overlap(own_raw, other_raw):
                    if _boxes_overlap(crop, other_raw):
                        raise AssertionError(
                            f"Shared page {surf} crop_box {crop_box} for {pid} overlaps "
                            f"co-tenant {other_pid} raw block {other_raw}"
                        )
                elif not (
                    crop[0] >= own_raw[0] - 32
                    and crop[1] >= own_raw[1] - 32
                    and crop[2] <= own_raw[2] + 32
                    and crop[3] <= own_raw[3] + 32
                ):
                    raise AssertionError(
                        f"Interleaved shared page {surf} crop_box {crop_box} for {pid} "
                        f"exceeds the 32px margin around its raw block {own_raw}"
                    )
            elif own_raw is not None and not (
                crop[0] >= own_raw[0] - 32
                and crop[1] >= own_raw[1] - 32
                and crop[2] <= own_raw[2] + 32
                and crop[3] <= own_raw[3] + 32
            ):
                raise AssertionError(
                    f"Shared page {surf} crop_box {crop_box} for {pid} exceeds the "
                    f"32px margin around its raw block {own_raw} (co-tenant bbox unavailable)"
                )
        if exp.get("exposed_other_blocks"):
            raise AssertionError(
                f"Shared page {surf} export for {pid} exposed other piece blocks"
            )


def assert_no_traceback(res: subprocess.CompletedProcess[str], label: str = "cli") -> None:
    """Fail closed when a target CLI crashes with an unhandled Python traceback."""
    combined = (res.stdout or "") + "\n" + (res.stderr or "")
    if "Traceback (most recent call last):" in combined:
        raise AssertionError(f"[{label}] unhandled traceback in CLI output:\n{combined[-800:]}")


def assert_cli_ok_or_handled_error(
    res: subprocess.CompletedProcess[str],
    label: str = "cli",
    handled_pattern: str = r"ocr|cache|missing|denied|not authorized|unavailable",
) -> bool:
    """Return True on rc==0; otherwise require a non-traceback handled error."""
    assert_no_traceback(res, label)
    if res.returncode == 0:
        return True
    combined = (res.stdout or "") + "\n" + (res.stderr or "")
    if not combined.strip():
        raise AssertionError(f"[{label}] non-zero exit with no diagnostic output")
    if not re.search(handled_pattern, combined, re.IGNORECASE):
        raise AssertionError(
            f"[{label}] non-zero exit without a handled error: {combined[-800:]}"
        )
    return False


def assert_preflight_contract(
    res: subprocess.CompletedProcess[str],
    label: str = "tndc preflight",
) -> dict[str, Any]:
    """Validate either the reference-stub or real-target preflight JSON contract."""
    assert_no_traceback(res, label)
    if res.returncode != 0:
        return {}
    try:
        payload = json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"[{label}] stdout is not valid JSON: {res.stdout[:400]!r}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"[{label}] JSON payload must be an object")
    stub_keys = {"photos_access", "notes_access", "photos_albums", "notes_folders"}
    real_keys = {"ready", "environment", "photos", "notes"}
    if not (payload.keys() & stub_keys) and not (payload.keys() & real_keys):
        raise AssertionError(f"[{label}] unrecognized preflight schema keys: {sorted(payload)[:10]}")
    return payload


def assert_two_repo_boundary_clean(jhw_root: Path) -> None:
    """AST + text scan ensuring JHW contains zero Apple Photos/Notes/Vision capture code."""
    scan_dirs = ("tools", "tests", "source")
    for rel_dir in scan_dirs:
        base = jhw_root / rel_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(jhw_root).as_posix()
            if path.suffix == ".py":
                src = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(src, filename=rel)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            top = alias.name.split(".")[0]
                            if top in FORBIDDEN_JHW_IMPORTS:
                                raise AssertionError(
                                    f"Forbidden import {alias.name!r} in {rel}:{node.lineno}"
                                )
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        top = node.module.split(".")[0]
                        if top in FORBIDDEN_JHW_IMPORTS:
                            raise AssertionError(
                                f"Forbidden from-import {node.module!r} in {rel}:{node.lineno}"
                            )
                # Skip literal string checks inside tests/e2e_witness itself (which asserts against them)
                if not rel.startswith("tests/e2e_witness/"):
                    for pat in FORBIDDEN_JHW_PATTERNS:
                        if pat in src:
                            raise AssertionError(f"Forbidden pattern {pat!r} in {rel}")
                    for mod in FORBIDDEN_JHW_IMPORTS:
                        if re.search(rf"\b{re.escape(mod)}\b", src):
                            raise AssertionError(f"Forbidden module mention {mod!r} in {rel}")


def snapshot_protected_hashes(jhw_root: Path) -> dict[str, str]:
    """Hash site/, studio/, MANIFEST.sha256, source/canonical.json, release/public.json."""
    snaps: dict[str, str] = {}
    for rel_file in ("MANIFEST.sha256", "source/canonical.json", "release/public.json"):
        p = jhw_root / rel_file
        if p.is_file():
            snaps[rel_file] = _file_sha256(p)
    for rel_dir in ("site", "studio"):
        d = jhw_root / rel_dir
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_file() and p.name != ".DS_Store":
                    snaps[p.relative_to(jhw_root).as_posix()] = _file_sha256(p)
    return snaps


def assert_protected_paths_unchanged(jhw_root: Path, before: dict[str, str]) -> None:
    after = snapshot_protected_hashes(jhw_root)
    if before != after:
        missing = sorted(set(before) - set(after))
        added = sorted(set(after) - set(before))
        changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
        raise AssertionError(
            f"Protected paths mutated! missing={missing[:5]}, added={added[:5]}, changed={changed[:5]}"
        )


def assert_git_clean(repo_dir: Path, label: str = "repo") -> None:
    res = subprocess.run(
        ["git", "-C", str(repo_dir), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        raise AssertionError(f"git status failed for {label} ({repo_dir}): {res.stderr}")
    if res.stdout.strip():
        raise AssertionError(f"{label} working tree is dirty:\n{res.stdout}")
