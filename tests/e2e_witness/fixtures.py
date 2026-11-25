"""Fixture generators, real-corpus indexers, and fault-injection corruptors."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import struct
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, ImageCms, ImageDraw, TiffImagePlugin

MARKUP_TAG_RE = re.compile(r"\[\[(?:struck|ins):\s*([^\]]*)\]\]")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def clean_transcript_line(line: str) -> str:
    """Strip inline [[struck: ...]] / [[ins: ...]] markers into plain text."""
    text = line
    for _ in range(4):
        updated = MARKUP_TAG_RE.sub(r"\1", text)
        if updated == text:
            break
        text = updated
    return " ".join(text.split())


class CorpusIndex:
    """Authoritative ground-truth index loaded from site/data/j.json & source/canonical.json."""

    def __init__(self, jhw_root: Path) -> None:
        self.jhw_root = Path(jhw_root)
        j_path = self.jhw_root / "site" / "data" / "j.json"
        c_path = self.jhw_root / "source" / "canonical.json"
        if not j_path.is_file():
            raise FileNotFoundError(f"Missing corpus file: {j_path}")
        if not c_path.is_file():
            raise FileNotFoundError(f"Missing canonical file: {c_path}")
        self.j_data: dict[str, Any] = json.loads(j_path.read_text(encoding="utf-8"))
        self.canonical_data: dict[str, Any] = json.loads(c_path.read_text(encoding="utf-8"))

        if "pages" not in self.j_data or "pieces" not in self.j_data:
            raise ValueError("Malformed j.json: missing 'pages' or 'pieces'")

        self.pages: list[dict[str, Any]] = self.j_data["pages"]
        self.page_by_id: dict[str, dict[str, Any]] = {p["id"]: p for p in self.pages}
        self.page_order: dict[str, int] = {p["id"]: idx for idx, p in enumerate(self.pages)}
        self.pieces: list[dict[str, Any]] = self.j_data["pieces"]
        self.piece_by_id: dict[str, dict[str, Any]] = {p["id"]: p for p in self.pieces}
        self.accepted_readings: dict[str, str] = self.j_data.get("acceptedReadings", {})

        self.canonical_masters: dict[str, str] = {
            a["pageId"]: a["sha256"]
            for a in self.canonical_data.get("assets", [])
            if a.get("role") == "preserved-jpeg-master" and a.get("pageId")
        }

        # Map each page_id -> set of distinct piece_ids appearing on it
        page_pieces: dict[str, set[str]] = {p["id"]: set() for p in self.pages}
        for piece in self.pieces:
            for ver in piece.get("V", []):
                for page_id, _blocks in ver.get("P", []):
                    if page_id in page_pieces:
                        page_pieces[page_id].add(piece["id"])

        self.multi_piece_pages: dict[str, list[str]] = {
            pid: sorted(pids) for pid, pids in page_pieces.items() if len(pids) > 1
        }
        self.spread_exposed_pages: dict[str, dict[str, Any]] = {}
        for page in self.pages:
            sp = page.get("sp") or {}
            if sp.get("f") or sp.get("s") == "whole spread" or sp.get("cb") is None:
                self.spread_exposed_pages[page["id"]] = sp

        self.multi_version_pieces: list[str] = [
            p["id"] for p in self.pieces if len(p.get("V", [])) > 1
        ]
        self.multi_page_versions: list[tuple[str, str, list[str]]] = []
        for piece in self.pieces:
            for ver in piece.get("V", []):
                p_list = [entry[0] for entry in ver.get("P", [])]
                if len(p_list) > 1:
                    self.multi_page_versions.append((piece["id"], ver["id"], p_list))

    def extract_version_text(
        self,
        piece_id: str,
        version_id: str | None = None,
        apply_accepted_readings: bool = True,
        strip_markup: bool = True,
    ) -> str:
        piece = self.piece_by_id[piece_id]
        versions = piece.get("V", [])
        if version_id is not None:
            ver = next(v for v in versions if v["id"] == version_id)
        else:
            top_idx = piece.get("top", 0)
            ver = versions[top_idx if 0 <= top_idx < len(versions) else 0]

        lines: list[str] = []
        for page_id, block_indices in ver.get("P", []):
            page = self.page_by_id[page_id]
            blocks = page.get("B", [])
            for b_idx in block_indices:
                if b_idx >= len(blocks):
                    continue
                for l_idx, raw_line in enumerate(blocks[b_idx].get("L", [])):
                    key = f"{page_id}-{b_idx}-{l_idx}"
                    line = (
                        self.accepted_readings[key]
                        if apply_accepted_readings and key in self.accepted_readings
                        else raw_line
                    )
                    if strip_markup:
                        line = clean_transcript_line(line)
                    if line:
                        lines.append(line)
        return "\n".join(lines)

    def piece_block_bbox(
        self,
        piece_id: str,
        page_id: str,
        version_id: str | None = None,
        pad: int = 8,
    ) -> tuple[int, int, int, int] | None:
        """Compute pixel crop box [left, top, right, bottom] for piece blocks on page_id.

        ``pad=0`` gives the exact raw ink bounds; the default 8px pad matches the
        reference projection CLI's conservative crop.
        """
        piece = self.piece_by_id[piece_id]
        versions = piece.get("V", [])
        ver = None
        if version_id is not None:
            ver = next((v for v in versions if v["id"] == version_id), None)
        else:
            for candidate in versions:
                if any(p == page_id for p, _ in candidate.get("P", [])):
                    ver = candidate
                    break
        if ver is None:
            return None
        target_blocks: set[int] = set()
        for p, blks in ver.get("P", []):
            if p == page_id:
                target_blocks.update(blks)
        page = self.page_by_id[page_id]
        iw, ih = int(page["iw"]), int(page["ih"])
        xs = [row for row in page.get("x", []) if row[0] in target_blocks]
        if not xs:
            return None
        margin = max(0, int(pad))
        x0 = max(0, int(min(r[2] for r in xs) * iw) - margin)
        y0 = max(0, int(min(r[3] for r in xs) * ih) - margin)
        x1 = min(iw, int(max(r[4] for r in xs) * iw) + margin)
        y1 = min(ih, int(max(r[5] for r in xs) * ih) + margin)
        if x1 <= x0 or y1 <= y0:
            return None
        return (x0, y0, x1, y1)


def _inject_ifd1_thumbnail(exif_bytes: bytes, thumb_jpeg: bytes) -> bytes:
    """Append IFD1 (0x0201 offset, 0x0202 length) + thumbnail JPEG into a TIFF/EXIF payload."""
    if not exif_bytes.startswith(b"Exif\x00\x00"):
        raise ValueError("Expected Exif header")
    tiff = exif_bytes[6:]
    endian = "<" if tiff[:2] == b"II" else ">"
    ifd0_off = struct.unpack(endian + "I", tiff[4:8])[0]
    count0 = struct.unpack(endian + "H", tiff[ifd0_off : ifd0_off + 2])[0]
    next_ptr_off = ifd0_off + 2 + count0 * 12

    ifd1_off = len(tiff)
    # 2 IFD entries: 0x0201 (JPEGInterchangeFormat), 0x0202 (JPEGInterchangeFormatLength)
    ifd1_size = 2 + 2 * 12 + 4
    thumb_off = ifd1_off + ifd1_size

    buf = bytearray(tiff)
    buf[next_ptr_off : next_ptr_off + 4] = struct.pack(endian + "I", ifd1_off)
    buf.extend(struct.pack(endian + "H", 2))
    buf.extend(struct.pack(endian + "HHII", 0x0201, 4, 1, thumb_off))
    buf.extend(struct.pack(endian + "HHII", 0x0202, 4, 1, len(thumb_jpeg)))
    buf.extend(struct.pack(endian + "I", 0))
    buf.extend(thumb_jpeg)
    return b"Exif\x00\x00" + bytes(buf)


def _inject_xmp_segment(jpeg_bytes: bytes, xmp_xml: str) -> bytes:
    """Insert an APP1 XMP segment right after JPEG SOI (0xFFD8)."""
    if not jpeg_bytes.startswith(b"\xff\xd8"):
        raise ValueError("Invalid JPEG bytes: missing SOI")
    payload = b"http://ns.adobe.com/xap/1.0/\x00" + xmp_xml.encode("utf-8")
    seg_len = len(payload) + 2
    segment = b"\xff\xe1" + struct.pack(">H", seg_len) + payload
    return jpeg_bytes[:2] + segment + jpeg_bytes[2:]


def build_metadata_laden_jpeg(
    out_path: Path,
    lines: list[str] | None = None,
    width: int = 400,
    height: int = 300,
    datetime_original: str = "2015:04:12 19:42:10",
    camera_make: str = "Apple",
    camera_model: str = "iPhone 6",
) -> Path:
    """Write a real JPEG carrying EXIF, GPS IFDRational, IFD1 thumbnail, ICC profile, and XMP."""
    img = Image.new("RGB", (width, height), color=(248, 246, 240))
    if lines:
        draw = ImageDraw.Draw(img)
        y = 24
        for line in lines:
            draw.text((24, y), line, fill=(20, 20, 20))
            y += 22

    # 32x32 embedded JPEG thumbnail
    thumb_img = img.resize((32, 32))
    thumb_buf = io.BytesIO()
    thumb_img.save(thumb_buf, format="JPEG", quality=75)
    thumb_jpeg = thumb_buf.getvalue()

    exif = Image.Exif()
    exif[0x010F] = camera_make
    exif[0x0110] = camera_model
    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
    exif_ifd[0x9003] = datetime_original
    exif_ifd[0x9004] = datetime_original

    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps_ifd[1] = "N"
    gps_ifd[2] = (
        TiffImagePlugin.IFDRational(40, 1),
        TiffImagePlugin.IFDRational(42, 1),
        TiffImagePlugin.IFDRational(46, 1),
    )
    gps_ifd[3] = "W"
    gps_ifd[4] = (
        TiffImagePlugin.IFDRational(74, 1),
        TiffImagePlugin.IFDRational(0, 1),
        TiffImagePlugin.IFDRational(21, 1),
    )

    exif_bytes = _inject_ifd1_thumbnail(exif.tobytes(), thumb_jpeg)
    icc_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()

    jpeg_buf = io.BytesIO()
    img.save(jpeg_buf, format="JPEG", quality=92, exif=exif_bytes, icc_profile=icc_profile)

    xmp_xml = (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        "<rdf:Description rdf:about='' xmlns:xmp='http://ns.adobe.com/xap/1.0/'>"
        f"<xmp:CreateDate>{datetime_original}</xmp:CreateDate>"
        "<xmp:CreatorTool>PrivatePhoneCapture</xmp:CreatorTool>"
        "</rdf:Description></rdf:RDF></x:xmpmeta>"
    )
    final_bytes = _inject_xmp_segment(jpeg_buf.getvalue(), xmp_xml)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(final_bytes)
    return out_path


def build_poem_image(
    out_path: Path,
    lines: list[str],
    width: int = 800,
    height: int = 600,
    with_metadata: bool = False,
) -> Path:
    """Create a synthetic high-contrast poem photo (optionally with real EXIF/XMP/GPS/ICC)."""
    if with_metadata:
        return build_metadata_laden_jpeg(out_path, lines=lines, width=width, height=height)
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    y = 32
    for line in lines:
        draw.text((32, y), line, fill=(10, 10, 10))
        y += 28
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = "PNG" if out_path.suffix.lower() == ".png" else "JPEG"
    img.save(out_path, format=fmt)
    return out_path


def build_blank_image(out_path: Path, width: int = 200, height: int = 200) -> Path:
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="JPEG")
    return out_path


def build_corrupt_file(out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(b"NOT_A_VALID_JPEG_HEADER_0000_CORRUPT")
    return out_path


def make_photo_witness(
    photo_uuid: str,
    original_filename: str,
    local_path: Path,
    witnessed_at: str,
    camera_model: str = "Apple iPhone 6",
    dimensions: list[int] | None = None,
    albums: list[str] | None = None,
    keywords: list[str] | None = None,
    is_in_icloud_only: bool = False,
) -> dict[str, Any]:
    digest = (
        sha256_file(local_path)
        if local_path.is_file()
        else sha256_bytes(f"missing:{photo_uuid}".encode("utf-8"))
    )
    return {
        "photo_uuid": photo_uuid,
        "original_filename": original_filename,
        "local_path": str(local_path),
        "photo_sha256": digest,
        "witnessed_at": witnessed_at,
        "camera_model": camera_model,
        "dimensions": dimensions or [800, 600],
        "albums": albums if albums is not None else ["Journal"],
        "keywords": keywords if keywords is not None else [],
        "is_in_icloud_only": is_in_icloud_only,
    }


def make_ios_note(
    note_id: str,
    folder: str,
    title: str,
    created_at: str,
    modified_at: str,
    plaintext: str,
) -> dict[str, Any]:
    return {
        "note_id": note_id,
        "folder": folder,
        "title": title,
        "created_at": created_at,
        "modified_at": modified_at,
        "plaintext": plaintext,
        "text_sha256": sha256_bytes(plaintext.encode("utf-8")),
    }


def write_intake_bundle(
    intake_dir: Path,
    photos: list[dict[str, Any]] | None = None,
    notes: list[dict[str, Any]] | None = None,
    ocr_cache: dict[str, dict[str, Any]] | None = None,
) -> Path:
    intake_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(intake_dir, 0o700)
    (intake_dir / "photos").mkdir(parents=True, exist_ok=True)
    os.chmod(intake_dir / "photos", 0o700)

    if photos is not None:
        sorted_photos = sorted(photos, key=lambda item: item["witnessed_at"])
        p_file = intake_dir / "photo_witnesses.json"
        p_file.write_text(json.dumps(sorted_photos, indent=2) + "\n", encoding="utf-8")
        os.chmod(p_file, 0o600)

    if notes is not None:
        sorted_notes = sorted(notes, key=lambda item: item["created_at"])
        n_file = intake_dir / "ios_notes.json"
        n_file.write_text(json.dumps(sorted_notes, indent=2) + "\n", encoding="utf-8")
        os.chmod(n_file, 0o600)

    if ocr_cache is not None:
        o_file = intake_dir / "ocr_cache.json"
        o_file.write_text(json.dumps(ocr_cache, indent=2) + "\n", encoding="utf-8")
        os.chmod(o_file, 0o600)

    return intake_dir


# --- Fault-injection corruptors (for Negative Controls & Tier 2 anti-tautology) ---


def inject_plaintext_into_witness_links(links: dict[str, Any]) -> dict[str, Any]:
    corrupted = json.loads(json.dumps(links))
    if corrupted.get("note_links"):
        corrupted["note_links"][0]["plaintext"] = "PRIVATE_LEAKED_NOTE_BODY"
    else:
        corrupted["note_links"] = [
            {
                "note_id": "n-leak",
                "text_sha256": sha256_bytes(b"leak"),
                "created_at": "2015-03-01T10:00:00-05:00",
                "modified_at": "2015-03-01T10:05:00-05:00",
                "candidates": [],
                "confirmed_piece_id": None,
                "status": "pending_review",
                "relation": "unreviewed",
                "plaintext": "PRIVATE_LEAKED_NOTE_BODY",
            }
        ]
    return corrupted


def inject_local_path_into_chronology(chron: dict[str, Any]) -> dict[str, Any]:
    corrupted = json.loads(json.dumps(chron))
    corrupted["physical_codex_order"][0]["local_path"] = "/Users/example/Private/IMG_999.jpg"
    return corrupted


def inject_digitized_at_into_chronology(
    chron: dict[str, Any],
    digitized_at: str = "2015-09",
) -> dict[str, Any]:
    corrupted = json.loads(json.dumps(chron))
    corrupted["physical_codex_order"][-1]["chronology"]["est_end"] = f"{digitized_at}-15"
    return corrupted


def inject_exif_into_jpeg(jpeg_path: Path, out_path: Path) -> Path:
    img = Image.open(jpeg_path)
    exif = Image.Exif()
    exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
    exif_ifd[0x9003] = "2015:09:15 12:00:00"
    img.save(out_path, format="JPEG", exif=exif.tobytes())
    return out_path


def inject_p126_leak_into_projection(
    manifest: dict[str, Any],
    corpus: CorpusIndex,
) -> dict[str, Any]:
    corrupted = json.loads(json.dumps(manifest))
    p126_box = corpus.piece_block_bbox("p126", "diary62a") or (0, 0, 1000, 1000)
    page62 = corpus.page_by_id["diary62a"]
    corrupted.setdefault("exports", []).append(
        {
            "piece_id": "p001",
            "surface_id": "diary62a",
            "isolated_crop": False,
            "blocks": [0, 1, 2, 3, 4],
            "crop_box": [0, 0, page62["iw"], page62["ih"]],
            "exposed_other_blocks": list(p126_box),
        }
    )
    return corrupted


def inject_pending_link_into_chronology(chron: dict[str, Any]) -> dict[str, Any]:
    corrupted = json.loads(json.dumps(chron))
    corrupted["physical_codex_order"][1]["witnesses"]["photo_witnesses"].append(
        {
            "photo_id": "ph-pending-leak",
            "photo_uuid": "UUID-PENDING-LEAK",
            "photo_sha256": sha256_bytes(b"pending"),
            "witnessed_at": "2014-01-01T00:00:00-05:00",
            "camera_model": "Apple iPhone 6",
            "textual_state": "unreviewed",
            "status": "pending_review",
        }
    )
    return corrupted


def inject_osxphotos_into_jhw_tools(jhw_sandbox: Path) -> Path:
    bad_file = jhw_sandbox / "tools" / "_bad_boundary_probe.py"
    bad_file.write_text("import osxphotos\n", encoding="utf-8")
    return bad_file
