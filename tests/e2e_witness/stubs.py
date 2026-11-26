"""Genuine subprocess-executed reference CLI drivers used ONLY under --self-check."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from .fixtures import CorpusIndex, clean_transcript_line

DEFAULT_INTAKE_DIR = Path("/Volumes/Archive4T/Media/intake/versforms-witnesses")


def _atomic_write_text(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _inside_git_tree(target: Path) -> Path | None:
    """Resolve symlinks and walk ancestors checking for .git file or directory."""
    resolved = target.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _default_photos_fixture() -> list[dict[str, Any]]:
    return [
        {
            "photo_uuid": "UUID-DEFAULT-001",
            "original_filename": "IMG_0001.JPG",
            "witnessed_at": "2015-03-10T14:00:00-04:00",
            "camera_model": "Apple iPhone 6",
            "dimensions": [800, 600],
            "albums": ["Journal"],
            "keywords": ["poem"],
            "ismovie": False,
            "intrash": False,
            "ismissing": False,
            "lines": ["The walls", "Collapse, like the seal", "youve sown:"],
        }
    ]


def _default_notes_fixture() -> list[dict[str, Any]]:
    return [
        {
            "note_id": "NOTE-DEFAULT-001",
            "folder": "4_bloom",
            "account": "iCloud",
            "title": "Untitled Draft",
            "created_at": "2015-03-12T20:00:00-04:00",
            "modified_at": "2015-03-12T20:05:00-04:00",
            "plaintext": "A Flower is a Flower, or a scream in the loneliest wilderness",
            "password_protected": False,
        }
    ]


def _load_stub_photos() -> list[dict[str, Any]]:
    p = os.environ.get("E2E_STUB_PHOTOS_JSON")
    if p and Path(p).is_file():
        return json.loads(Path(p).read_text(encoding="utf-8"))
    return _default_photos_fixture()


def _load_stub_notes() -> list[dict[str, Any]]:
    p = os.environ.get("E2E_STUB_NOTES_JSON")
    if p and Path(p).is_file():
        return json.loads(Path(p).read_text(encoding="utf-8"))
    return _default_notes_fixture()


def _cmd_tndc_preflight(args: argparse.Namespace) -> int:
    if os.environ.get("E2E_STUB_TCC_DENIED") == "1":
        sys.stderr.write(
            "ERROR: Apple Photos access denied.\n"
            "Open System Settings -> Privacy & Security -> Full Disk Access and enable your terminal.\n"
        )
        return 1
    if os.environ.get("E2E_STUB_AUTOMATION_DENIED") == "1":
        sys.stderr.write(
            "ERROR: Apple Notes automation denied (-1743).\n"
            "Open System Settings -> Privacy & Security -> Automation and allow Notes control.\n"
        )
        return 1

    photos = _load_stub_photos()
    notes = _load_stub_notes()

    album_counts: dict[str, int] = {}
    extra_albums = os.environ.get("E2E_STUB_EXTRA_ALBUMS")
    if extra_albums:
        for name in json.loads(extra_albums):
            album_counts.setdefault(name, 0)
    for ph in photos:
        if ph.get("ismovie") or ph.get("intrash"):
            continue
        for alb in ph.get("albums", []):
            album_counts[alb] = album_counts.get(alb, 0) + 1

    folder_counts: list[dict[str, Any]] = []
    seen_folders: dict[tuple[str, str], int] = {}
    extra_folders = os.environ.get("E2E_STUB_EXTRA_FOLDERS")
    if extra_folders:
        for entry in json.loads(extra_folders):
            key = (entry.get("account", "iCloud"), entry["folder"])
            seen_folders.setdefault(key, 0)
    for nt in notes:
        key = (nt.get("account", "iCloud"), nt["folder"])
        seen_folders[key] = seen_folders.get(key, 0) + 1
    for (acct, folder), cnt in sorted(seen_folders.items()):
        folder_counts.append({"account": acct, "folder": folder, "count": cnt})

    payload = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "dependencies": {"osxphotos": "ok", "rapidfuzz": "ok", "ocrmac": "ok", "Vision": "ok"},
        "photos_access": "ok (osxphotos.PhotosDB)",
        "notes_access": "ok (osascript -l JavaScript Application('Notes'))",
        "photos_albums": [{"album": k, "count": v} for k, v in sorted(album_counts.items())],
        "notes_folders": folder_counts,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Python {payload['python']} OK; Photos OK; Notes OK")
        for alb in payload["photos_albums"]:
            print(f"ALBUM {alb['album']!r}: {alb['count']}")
        for fld in payload["notes_folders"]:
            print(f"FOLDER ({fld['account']}) {fld['folder']!r}: {fld['count']}")
    return 0


def _run_ocr_on_dir(out_dir: Path) -> int:
    pw_path = out_dir / "photo_witnesses.json"
    if not pw_path.is_file():
        sys.stderr.write(f"Missing photo_witnesses.json in {out_dir}\n")
        return 1
    photos = json.loads(pw_path.read_text(encoding="utf-8"))
    cache_path = out_dir / "ocr_cache.json"
    existing: dict[str, Any] = {}
    if cache_path.is_file():
        existing = json.loads(cache_path.read_text(encoding="utf-8"))

    ocr_map_raw = os.environ.get("E2E_STUB_OCR_TEXT_MAP")
    ocr_map: dict[str, str] = json.loads(ocr_map_raw) if ocr_map_raw else {}

    updated = dict(existing)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for ph in photos:
        uuid = ph["photo_uuid"]
        if uuid in existing:
            continue
        local_path = Path(ph["local_path"])
        if not local_path.is_file():
            updated[uuid] = {
                "text": "",
                "lines": [],
                "ocr_engine": "Vision.VNRecognizeTextRequest",
                "ocr_at": now_iso,
                "error": f"missing file: {local_path.name}",
            }
            continue
        try:
            with Image.open(local_path) as img:
                img.verify()
            with Image.open(local_path) as img2:
                extrema = img2.convert("RGB").getextrema()
                is_blank = all(lo == hi for lo, hi in extrema)
        except Exception as exc:
            updated[uuid] = {
                "text": "",
                "lines": [],
                "ocr_engine": "Vision.VNRecognizeTextRequest",
                "ocr_at": now_iso,
                "error": f"unreadable image: {exc}",
            }
            continue

        if uuid in ocr_map:
            text = ocr_map[uuid]
        elif is_blank:
            text = ""
        else:
            text = " ".join(ph.get("stub_lines", [])) or f"OCR recognized witness {uuid}"
        lines = [ln for ln in text.splitlines() if ln.strip()]
        updated[uuid] = {
            "text": text,
            "lines": lines,
            "ocr_engine": "Vision.VNRecognizeTextRequest",
            "ocr_at": now_iso,
        }

    _atomic_write_text(cache_path, json.dumps(updated, indent=2) + "\n", mode=0o600)
    return 0


def _cmd_tndc_witness(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir) if args.out_dir else DEFAULT_INTAKE_DIR
    git_root = _inside_git_tree(out_dir)
    if git_root is not None and not args.allow_git_dir_for_tests:
        sys.stderr.write(
            f"REFUSED: --out-dir {out_dir} resolves inside git working tree {git_root}. "
            "Raw personal captures must stay outside git.\n"
        )
        return 1

    if args.max_year is not None:
        try:
            max_year = int(args.max_year)
        except ValueError:
            sys.stderr.write(f"Invalid --max-year: {args.max_year!r}\n")
            return 2
    else:
        max_year = None

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "planned_out_dir": str(out_dir),
                    "photos_album": args.photos_album,
                    "notes_folder": args.notes_folder,
                    "max_year": max_year,
                }
            )
        )
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(out_dir, 0o700)
    photos_dir = out_dir / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(photos_dir, 0o700)

    if not args.ocr_only:
        raw_photos = _load_stub_photos()
        exported_photos: list[dict[str, Any]] = []
        for ph in raw_photos:
            if ph.get("ismovie") or ph.get("intrash"):
                continue
            if args.photos_album:
                if not any(a in args.photos_album for a in ph.get("albums", [])):
                    continue
            w_at = str(ph["witnessed_at"])
            year = int(w_at[:4])
            if max_year is not None and year > max_year:
                continue

            uuid = ph["photo_uuid"]
            orig = ph["original_filename"]
            dest = photos_dir / f"{uuid}_{orig}"
            is_missing = bool(ph.get("ismissing", False))
            icloud_only = False
            if is_missing and not args.download_missing:
                icloud_only = True
                sha = _sha256_text(f"icloud:{uuid}")
            else:
                if not dest.exists():
                    src_img = ph.get("source_path")
                    if src_img and Path(src_img).is_file():
                        shutil.copy2(src_img, dest)
                    else:
                        img = Image.new("RGB", tuple(ph.get("dimensions", [400, 300])), (250, 250, 250))
                        img.save(dest, format="JPEG")
                    os.chmod(dest, 0o600)
                sha = _sha256_file(dest)

            exported_photos.append(
                {
                    "photo_uuid": uuid,
                    "original_filename": orig,
                    "local_path": str(dest),
                    "photo_sha256": sha,
                    "witnessed_at": w_at,
                    "camera_model": ph.get("camera_model", "Apple iPhone 6"),
                    "dimensions": ph.get("dimensions", [400, 300]),
                    "albums": ph.get("albums", []),
                    "keywords": ph.get("keywords", []),
                    "is_in_icloud_only": icloud_only,
                }
            )
        exported_photos.sort(key=lambda item: item["witnessed_at"])
        _atomic_write_text(
            out_dir / "photo_witnesses.json",
            json.dumps(exported_photos, indent=2) + "\n",
            mode=0o600,
        )

        raw_notes = _load_stub_notes()
        exported_notes: list[dict[str, Any]] = []
        for nt in raw_notes:
            if nt.get("password_protected"):
                continue
            folder = str(nt["folder"])
            if args.notes_folder:
                targets = set(args.notes_folder)
                if folder not in targets and folder.strip() not in {t.strip() for t in targets}:
                    continue
            plaintext = str(nt.get("plaintext", ""))
            exported_notes.append(
                {
                    "note_id": nt["note_id"],
                    "folder": folder,
                    "title": nt.get("title", ""),
                    "created_at": nt["created_at"],
                    "modified_at": nt.get("modified_at", nt["created_at"]),
                    "plaintext": plaintext,
                    "text_sha256": _sha256_text(plaintext),
                }
            )
        exported_notes.sort(key=lambda item: item["created_at"])
        _atomic_write_text(
            out_dir / "ios_notes.json",
            json.dumps(exported_notes, indent=2) + "\n",
            mode=0o600,
        )

    if args.ocr or args.ocr_only:
        rc = _run_ocr_on_dir(out_dir)
        if rc != 0:
            return rc

    return 0


def _score_texts(query: str, target: str) -> tuple[float, float, float]:
    q_norm = " ".join(re.findall(r"[a-z0-9']+", query.lower()))
    t_norm = " ".join(re.findall(r"[a-z0-9']+", target.lower()))
    if not q_norm or not t_norm:
        return 0.0, 0.0, 0.0
    q_tokens = set(q_norm.split())
    t_tokens = set(t_norm.split())
    overlap = len(q_tokens & t_tokens) / max(1, min(len(q_tokens), len(t_tokens)))
    seq_ratio = difflib.SequenceMatcher(None, q_norm, t_norm).ratio()
    # Boost exact token-set alignment
    fuzzy = max(seq_ratio, overlap * 0.95)
    combined = round(0.45 * overlap + 0.55 * fuzzy, 4)
    return combined, round(overlap, 4), round(fuzzy, 4)


def _cmd_jhw_match(args: argparse.Namespace) -> int:
    intake_dir = Path(args.intake_dir)
    if not intake_dir.is_dir():
        sys.stderr.write(f"Missing --intake-dir: {intake_dir}\n")
        return 1
    j_path = Path(args.j_json)
    if not j_path.is_file():
        sys.stderr.write(f"Missing j.json: {j_path}\n")
        return 1

    pw_path = intake_dir / "photo_witnesses.json"
    notes_path = intake_dir / "ios_notes.json"
    if not pw_path.is_file() or not notes_path.is_file():
        sys.stderr.write("Missing photo_witnesses.json or ios_notes.json in intake dir\n")
        return 1

    photos = json.loads(pw_path.read_text(encoding="utf-8"))
    notes = json.loads(notes_path.read_text(encoding="utf-8"))
    ocr_path = intake_dir / "ocr_cache.json"
    if not ocr_path.is_file() and args.ocr_cmd:
        cmd = args.ocr_cmd.replace("{intake_dir}", str(intake_dir))
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            sys.stderr.write(f"OCR hook failed: {res.stderr}\n")
            return res.returncode

    ocr_cache: dict[str, Any] = (
        json.loads(ocr_path.read_text(encoding="utf-8")) if ocr_path.is_file() else {}
    )

    corpus = CorpusIndex(j_path.parent.parent.parent)
    piece_texts: dict[str, str] = {}
    for p in corpus.pieces:
        pid = p["id"]
        parts = [
            corpus.extract_version_text(pid, v["id"], apply_accepted_readings=True, strip_markup=True)
            for v in p.get("V", [])
        ]
        piece_texts[pid] = "\n".join(parts)

    out_path = Path(args.out)
    prev_photos: dict[str, dict[str, Any]] = {}
    prev_notes: dict[str, dict[str, Any]] = {}
    if out_path.is_file():
        prev = json.loads(out_path.read_text(encoding="utf-8"))
        prev_photos = {item["photo_uuid"]: item for item in prev.get("photo_links", [])}
        prev_notes = {item["note_id"]: item for item in prev.get("note_links", [])}

    def _top3(query_text: str) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        for pid, ptext in piece_texts.items():
            score, overlap, fuzzy = _score_texts(query_text, ptext)
            if score > 0.0:
                scored.append(
                    {
                        "piece_id": pid,
                        "score": score,
                        "token_overlap": overlap,
                        "fuzzy_score": fuzzy,
                    }
                )
        scored.sort(key=lambda c: (-c["score"], c["piece_id"]))
        return scored[:3]

    photo_links: list[dict[str, Any]] = []
    review_lines = ["# Witness Review Report\n"]
    high_cnt = 0
    ambig_cnt = 0
    unmatched_cnt = 0

    for idx, ph in enumerate(photos, 1):
        uuid = ph["photo_uuid"]
        ocr_text = ocr_cache.get(uuid, {}).get("text", "")
        cands = _top3(ocr_text)
        top_score = cands[0]["score"] if cands else 0.0
        if top_score >= 0.7:
            high_cnt += 1
        elif top_score >= 0.25:
            ambig_cnt += 1
        else:
            unmatched_cnt += 1

        old = prev_photos.get(uuid)
        if old and old.get("status") in {"confirmed", "rejected"}:
            entry = dict(old)
            entry["candidates"] = cands
        else:
            entry = {
                "photo_id": f"ph-{idx:03d}",
                "photo_uuid": uuid,
                "photo_sha256": ph["photo_sha256"],
                "witnessed_at": ph["witnessed_at"],
                "camera_model": ph.get("camera_model", ""),
                "candidates": cands,
                "confirmed_piece_id": None,
                "status": "pending_review",
                "textual_state": "unreviewed",
            }
        photo_links.append(entry)
        review_lines.append(
            f"- Photo {uuid} ({ph['local_path']}): top={cands[:1]} | OCR={ocr_text[:120]!r}\n"
        )

    note_links: list[dict[str, Any]] = []
    for nt in notes:
        nid = nt["note_id"]
        plaintext = nt.get("plaintext", "")
        cands = _top3(plaintext)
        top_score = cands[0]["score"] if cands else 0.0
        if top_score >= 0.7:
            high_cnt += 1
        elif top_score >= 0.25:
            ambig_cnt += 1
        else:
            unmatched_cnt += 1

        old = prev_notes.get(nid)
        if old and old.get("status") in {"confirmed", "rejected"}:
            entry = dict(old)
            entry["candidates"] = cands
        else:
            entry = {
                "note_id": nid,
                "text_sha256": nt["text_sha256"],
                "created_at": nt["created_at"],
                "modified_at": nt["modified_at"],
                "candidates": cands,
                "confirmed_piece_id": None,
                "status": "pending_review",
                "relation": "unreviewed",
            }
        note_links.append(entry)
        review_lines.append(
            f"- Note {nid} ({nt.get('folder','')}/{nt.get('title','')}): "
            f"top={cands[:1]} | text={plaintext[:120]!r}\n"
        )

    out_payload = {
        "schema": "versforms.witness-links.v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "intake_summary": {
            "photos": len(photo_links),
            "notes": len(note_links),
            "high_confidence": high_cnt,
            "ambiguous": ambig_cnt,
            "unmatched": unmatched_cnt,
        },
        "photo_links": photo_links,
        "note_links": note_links,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")

    # Write verbose snippet report strictly into --intake-dir (outside git)
    report_path = intake_dir / "review_report.md"
    report_path.write_text("".join(review_lines), encoding="utf-8")

    print(
        f"match_witnesses: photos={len(photo_links)} notes={len(note_links)} "
        f"high={high_cnt} ambiguous={ambig_cnt} unmatched={unmatched_cnt}"
    )
    return 0


def _parse_iso_dt(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _cmd_jhw_chronology(args: argparse.Namespace) -> int:
    links_path = Path(args.links)
    j_path = Path(args.j_json)
    c_path = Path(args.canonical)
    if not links_path.is_file() or not j_path.is_file() or not c_path.is_file():
        sys.stderr.write("Missing required input file for build_chronology\n")
        return 1

    links = json.loads(links_path.read_text(encoding="utf-8"))
    corpus = CorpusIndex(j_path.parent.parent.parent)

    confirmed_photos_by_piece: dict[str, list[dict[str, Any]]] = {}
    for pl in links.get("photo_links", []):
        if pl.get("status") != "confirmed" or not pl.get("confirmed_piece_id"):
            continue
        pid = pl["confirmed_piece_id"]
        confirmed_photos_by_piece.setdefault(pid, []).append(
            {
                "photo_id": pl["photo_id"],
                "photo_uuid": pl["photo_uuid"],
                "photo_sha256": pl["photo_sha256"],
                "witnessed_at": pl["witnessed_at"],
                "camera_model": pl.get("camera_model", ""),
                "textual_state": pl.get("textual_state", "matches_scan"),
            }
        )

    confirmed_notes_by_piece: dict[str, list[dict[str, Any]]] = {}
    standalone_notes: list[dict[str, Any]] = []
    for nl in links.get("note_links", []):
        if nl.get("status") != "confirmed":
            continue
        pid = nl.get("confirmed_piece_id")
        note_rec = {
            "note_id": nl["note_id"],
            "created_at": nl["created_at"],
            "modified_at": nl["modified_at"],
            "relation": nl.get("relation", "standalone_cohort"),
        }
        if pid:
            confirmed_notes_by_piece.setdefault(pid, []).append(note_rec)
        else:
            standalone_notes.append(note_rec)

    # Map piece_id -> primary surface page index
    piece_page: dict[str, str] = {}
    piece_page_idx: dict[str, int] = {}
    for p in corpus.pieces:
        pid = p["id"]
        top_idx = p.get("top", 0)
        vers = p.get("V", [])
        ver = vers[top_idx if 0 <= top_idx < len(vers) else 0]
        surf = ver["P"][0][0]
        piece_page[pid] = surf
        piece_page_idx[pid] = corpus.page_order[surf]

    # Collect page-level anchors from confirmed photos (NEVER using digitized_at!)
    anchors_by_page_idx: dict[int, tuple[datetime, str]] = {}
    for pid, pws in confirmed_photos_by_piece.items():
        p_idx = piece_page_idx[pid]
        earliest = min(pws, key=lambda w: _parse_iso_dt(w["witnessed_at"]))
        dt = _parse_iso_dt(earliest["witnessed_at"])
        if p_idx not in anchors_by_page_idx or dt < anchors_by_page_idx[p_idx][0]:
            anchors_by_page_idx[p_idx] = (dt, earliest["photo_id"])

    sorted_anchors = sorted(anchors_by_page_idx.items(), key=lambda kv: kv[0])
    velocity_days = 0.0
    if len(sorted_anchors) >= 2:
        idx0, (dt0, _) = sorted_anchors[0]
        idx1, (dt1, _) = sorted_anchors[-1]
        if idx1 > idx0:
            raw_days = (dt1 - dt0).total_seconds() / 86400.0
            velocity_days = max(0.0, raw_days / float(idx1 - idx0))

    codex_entries: list[dict[str, Any]] = []
    amalg_entries: list[dict[str, Any]] = []

    ordered_pieces = sorted(corpus.pieces, key=lambda p: (piece_page_idx[p["id"]], p["id"]))
    for p in ordered_pieces:
        pid = p["id"]
        surf = piece_page[pid]
        p_idx = piece_page_idx[pid]
        pws = confirmed_photos_by_piece.get(pid, [])
        lns = confirmed_notes_by_piece.get(pid, [])

        if p_idx in anchors_by_page_idx:
            anchor_dt, anchor_id = anchors_by_page_idx[p_idx]
            prev_anc = next((a[1][1] for a in reversed(sorted_anchors) if a[0] < p_idx), None)
            next_anc = next((a[1][1] for a in sorted_anchors if a[0] > p_idx), None)
            date_basis = "photo_anchored"
            est_dt = anchor_dt
            est_start = (anchor_dt - timedelta(days=4)).strftime("%Y-%m-%d")
            est_end = anchor_dt.strftime("%Y-%m-%d")
            sort_ts = anchor_dt.strftime("%Y-%m-%dT%H:%M:%S")
        elif not sorted_anchors:
            date_basis = "undated"
            est_start = None
            est_end = None
            prev_anc = None
            next_anc = None
            sort_ts = f"undated#{p_idx:03d}"
        else:
            prev_list = [a for a in sorted_anchors if a[0] < p_idx]
            next_list = [a for a in sorted_anchors if a[0] > p_idx]
            if prev_list and next_list:
                a_idx, (a_dt, a_id) = prev_list[-1]
                b_idx, (b_dt, b_id) = next_list[0]
                frac = (p_idx - a_idx) / float(b_idx - a_idx)
                lo_dt, hi_dt = (a_dt, b_dt) if a_dt <= b_dt else (b_dt, a_dt)
                est_dt = lo_dt + timedelta(seconds=(hi_dt - lo_dt).total_seconds() * frac)
                date_basis = "interpolated"
                est_start = lo_dt.strftime("%Y-%m-%d")
                est_end = hi_dt.strftime("%Y-%m-%d")
                prev_anc = a_id
                next_anc = b_id
                sort_ts = est_dt.strftime("%Y-%m-%dT%H:%M:%S")
            elif next_list:
                b_idx, (b_dt, b_id) = next_list[0]
                date_basis = "extrapolated_head"
                prev_anc = None
                next_anc = b_id
                if len(sorted_anchors) >= 2:
                    est_dt = b_dt - timedelta(days=velocity_days * (b_idx - p_idx))
                    est_start = est_dt.strftime("%Y-%m-%d")
                    est_end = est_dt.strftime("%Y-%m-%d")
                    sort_ts = est_dt.strftime("%Y-%m-%dT%H:%M:%S")
                else:
                    est_start = None
                    est_end = None
                    sort_ts = f"undated#{p_idx:03d}"
            else:
                a_idx, (a_dt, a_id) = prev_list[-1]
                date_basis = "extrapolated_tail"
                prev_anc = a_id
                next_anc = None
                if len(sorted_anchors) >= 2:
                    est_dt = a_dt + timedelta(days=velocity_days * (p_idx - a_idx))
                    est_start = est_dt.strftime("%Y-%m-%d")
                    est_end = est_dt.strftime("%Y-%m-%d")
                    sort_ts = est_dt.strftime("%Y-%m-%dT%H:%M:%S")
                else:
                    est_start = None
                    est_end = None
                    sort_ts = f"undated#{p_idx:03d}"

        sort_key = f"{sort_ts}#{pid}"
        entry = {
            "piece_id": pid,
            "witnesses": {
                "codex_scan": {
                    "surface_id": surf,
                    "scan_sha256": corpus.canonical_masters.get(surf, ""),
                    "digitized_at": args.digitized_at,
                    "shared_surface": surf in corpus.multi_piece_pages,
                },
                "photo_witnesses": pws,
                "linked_ios_notes": lns,
            },
            "chronology": {
                "date_basis": date_basis,
                "est_start": est_start,
                "est_end": est_end,
                "anchor_prev": prev_anc,
                "anchor_next": next_anc,
                "amalgamated_sort_key": sort_key,
            },
        }
        codex_entries.append(entry)
        amalg_entries.append(
            {
                "entry_type": "piece",
                "sort_key": sort_key,
                "piece_id": pid,
                "surface_id": surf,
                "date_basis": date_basis,
            }
        )

    for nl in links.get("note_links", []):
        if nl.get("status") != "confirmed":
            continue
        c_at = _parse_iso_dt(nl["created_at"]).strftime("%Y-%m-%dT%H:%M:%S")
        amalg_entries.append(
            {
                "entry_type": "ios_note",
                "sort_key": f"{c_at}#{nl['note_id']}",
                "note_id": nl["note_id"],
                "piece_id": nl.get("confirmed_piece_id"),
                "relation": nl.get("relation", "standalone_cohort"),
            }
        )

    amalg_entries.sort(
        key=lambda item: (
            1 if str(item["sort_key"]).startswith("undated#") else 0,
            str(item["sort_key"]),
        )
    )

    out_payload = {
        "schema": "versforms.chronology.v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "digitized_at": args.digitized_at,
        "physical_codex_order": codex_entries,
        "amalgamated_chronological_order": amalg_entries,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_payload, indent=2) + "\n", encoding="utf-8")
    return 0


def _cmd_jhw_export(args: argparse.Namespace) -> int:
    chron_path = Path(args.chronology)
    j_path = Path(args.j_json)
    out_dir = Path(args.out_dir)
    if not chron_path.is_file() or not j_path.is_file():
        sys.stderr.write("Missing chronology.json or j.json\n")
        return 1

    chron = json.loads(chron_path.read_text(encoding="utf-8"))
    jhw_root = j_path.parent.parent.parent
    corpus = CorpusIndex(jhw_root)
    entry_map = {e["piece_id"]: e for e in chron["physical_codex_order"]}

    req_pieces = args.piece if args.piece else ["p001"]
    for pid in req_pieces:
        if pid not in corpus.piece_by_id:
            sys.stderr.write(f"Unknown piece_id: {pid!r}\n")
            return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    exports: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for pid in req_pieces:
        entry = entry_map[pid]
        surf = args.surface or entry["witnesses"]["codex_scan"]["surface_id"]
        src_img = Path(args.override_image) if args.override_image else (jhw_root / "site" / "img" / "p" / f"{surf}.jpg")
        if not src_img.is_file():
            sys.stderr.write(f"Missing source scan: {src_img}\n")
            return 1

        is_shared = surf in corpus.multi_piece_pages
        is_spread = surf in corpus.spread_exposed_pages

        if is_spread and not args.allow_spread_crop:
            blocked.append(
                {
                    "piece_id": pid,
                    "surface_id": surf,
                    "reason": "spread_exposed_surface_requires_isolation",
                }
            )
            continue

        with Image.open(src_img) as img:
            rgb = img.convert("RGB")
            crop_box = [0, 0, rgb.width, rgb.height]
            isolated_crop = False
            if is_shared:
                if args.no_crop:
                    blocked.append(
                        {
                            "piece_id": pid,
                            "surface_id": surf,
                            "reason": "co_tenanted_surface_blocked_without_crop",
                        }
                    )
                    continue
                bbox = corpus.piece_block_bbox(pid, surf)
                if bbox is None:
                    blocked.append(
                        {
                            "piece_id": pid,
                            "surface_id": surf,
                            "reason": "missing_block_bbox_for_shared_surface",
                        }
                    )
                    continue
                rgb = rgb.crop(bbox)
                crop_box = list(bbox)
                isolated_crop = True

            clean = Image.new("RGB", rgb.size)
            clean.paste(rgb)
            out_name = f"{pid}_{surf}.jpg"
            out_file = out_dir / out_name
            clean.save(out_file, format="JPEG", quality=92)

        exports.append(
            {
                "piece_id": pid,
                "surface_id": surf,
                "output_file": out_name,
                "sha256": _sha256_file(out_file),
                "shared_surface": is_shared,
                "isolated_crop": isolated_crop,
                "crop_box": crop_box,
                "dimensions": [clean.width, clean.height],
                "chronology_window": [
                    entry["chronology"]["est_start"],
                    entry["chronology"]["est_end"],
                ],
                "amalgamated_sort_key": entry["chronology"]["amalgamated_sort_key"],
            }
        )

    manifest = {
        "schema": "versforms.round1-projection.v1",
        "exports": exports,
        "blocked": blocked,
    }
    (out_dir / "projection_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    if args.strict and blocked and not exports:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="e2e-stubs")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ver = sub.add_parser("tndc-version")
    p_ver.set_defaults(func=lambda _a: (print("notes-docs-capture 0.1.0"), 0)[1])

    p_py = sub.add_parser("tndc-py-check")
    p_py.set_defaults(
        func=lambda _a: (
            print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
            0,
        )[1]
    )

    p_stat = sub.add_parser("tndc-status")
    p_stat.add_argument("--state-dir", required=True)
    p_stat.add_argument("--output-dir", required=True)
    p_stat.set_defaults(func=lambda a: (print(json.dumps({"ok": True, "state_dir": a.state_dir})), 0)[1])

    p_cap = sub.add_parser("tndc-capture-notes")
    p_cap.add_argument("--state-dir", required=True)
    p_cap.add_argument("--output-dir", required=True)
    p_cap.add_argument("--dry-run", action="store_true")
    p_cap.set_defaults(func=lambda _a: (print(json.dumps({"dry_run": True, "notes": []})), 0)[1])

    p_pre = sub.add_parser("tndc-preflight")
    p_pre.add_argument("--photos-album", action="append", default=[])
    p_pre.add_argument("--notes-folder", action="append", default=[])
    p_pre.add_argument("--json", action="store_true")
    p_pre.set_defaults(func=_cmd_tndc_preflight)

    p_wit = sub.add_parser("tndc-witness")
    p_wit.add_argument("--photos-album", action="append", default=[])
    p_wit.add_argument("--notes-folder", action="append", default=[])
    p_wit.add_argument("--max-year", default=None)
    p_wit.add_argument("--download-missing", action="store_true")
    p_wit.add_argument("--dry-run", action="store_true")
    p_wit.add_argument("--ocr", action="store_true")
    p_wit.add_argument("--ocr-only", action="store_true")
    p_wit.add_argument("--out-dir", default=None)
    p_wit.add_argument("--allow-git-dir-for-tests", action="store_true")
    p_wit.set_defaults(func=_cmd_tndc_witness)

    p_test = sub.add_parser("tndc-test-suite")
    p_test.set_defaults(
        func=lambda _a: 1 if os.environ.get("E2E_STUB_FAIL_TESTS") == "1" else 0
    )

    p_ruff = sub.add_parser("tndc-ruff")
    p_ruff.set_defaults(
        func=lambda _a: 1 if os.environ.get("E2E_STUB_FAIL_RUFF") == "1" else 0
    )

    p_m = sub.add_parser("jhw-match")
    p_m.add_argument("--intake-dir", default=str(DEFAULT_INTAKE_DIR))
    p_m.add_argument("--j-json", default="site/data/j.json")
    p_m.add_argument("--out", default="source/witness_links.json")
    p_m.add_argument("--ocr-cmd", default=None)
    p_m.set_defaults(func=_cmd_jhw_match)

    p_c = sub.add_parser("jhw-chronology")
    p_c.add_argument("--links", default="source/witness_links.json")
    p_c.add_argument("--j-json", default="site/data/j.json")
    p_c.add_argument("--canonical", default="source/canonical.json")
    p_c.add_argument("--out", default="source/chronology.json")
    p_c.add_argument("--digitized-at", default="2015-09")
    p_c.set_defaults(func=_cmd_jhw_chronology)

    p_e = sub.add_parser("jhw-export")
    p_e.add_argument("--chronology", default="source/chronology.json")
    p_e.add_argument("--j-json", default="site/data/j.json")
    p_e.add_argument("--out-dir", required=True)
    p_e.add_argument("--piece", action="append", default=[])
    p_e.add_argument("--surface", default=None)
    p_e.add_argument("--override-image", default=None)
    p_e.add_argument("--no-crop", action="store_true")
    p_e.add_argument("--allow-spread-crop", action="store_true")
    p_e.add_argument("--strict", action="store_true")
    p_e.set_defaults(func=_cmd_jhw_export)

    parsed = parser.parse_args(argv)
    return int(parsed.func(parsed))


if __name__ == "__main__":
    sys.exit(main())
