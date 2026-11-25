#!/usr/bin/env python3
"""Stage 2 witness candidate matcher for journal-handwritten-web.

Reads external raw intake metadata (photo_witnesses.json, ios_notes.json,
ocr_cache.json) from --intake-dir, scores each photo's OCR text and each note's
plaintext against all 126 transcribed pieces in site/data/j.json using
IDF-weighted token overlap + rapidfuzz, and writes public-safe candidate links
to source/witness_links.json while keeping snippet-rich review reports strictly
outside any git working tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None  # Checked before scoring so CLI exits non-zero with guidance

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTAKE_DIR = Path("/Volumes/Archive4T/Media/intake/versforms-witnesses")
SCHEMA_VERSION = "versforms.witness-links.v1"

HIGH_CONFIDENCE_MIN = 0.72
HIGH_CONFIDENCE_MARGIN = 0.10
AMBIGUOUS_MIN = 0.40

FORBIDDEN_PUBLIC_KEYS = frozenset({
    "plaintext",
    "title",
    "folder",
    "local_path",
    "ocr_text",
    "text",
    "lines",
    "snippet",
    "snippets",
    "raw_text",
    "albums",
    "keywords",
    "original_filename",
})

PHOTO_ALLOWED_KEYS = (
    "photo_id",
    "photo_uuid",
    "photo_sha256",
    "witnessed_at",
    "camera_model",
    "candidates",
    "confirmed_piece_id",
    "status",
    "textual_state",
)

NOTE_ALLOWED_KEYS = (
    "note_id",
    "text_sha256",
    "created_at",
    "modified_at",
    "candidates",
    "confirmed_piece_id",
    "status",
    "relation",
)

CANDIDATE_ALLOWED_KEYS = (
    "piece_id",
    "score",
    "token_overlap",
    "fuzzy_score",
)


@dataclass(frozen=True)
class VersionIndex:
    piece_id: str
    version_id: str
    clean_norm: str
    clean_tokens: tuple[str, ...]
    clean_set: frozenset[str]
    auth_norm: str
    auth_tokens: tuple[str, ...]
    auth_set: frozenset[str]
    preview: str


@dataclass(frozen=True)
class CorpusIndex:
    versions: tuple[VersionIndex, ...]
    idf: dict[str, float]
    pieces_count: int
    versions_count: int
    piece_previews: dict[str, str]


def parse_markup(raw: str) -> list[dict[str, Any]]:
    """Parse site/data/j.json inline [[...]] transcript markup."""
    out: list[dict[str, Any]] = []
    i = 0
    buf: list[str] = []
    n = len(raw)
    while i < n:
        if raw.startswith("[[", i):
            j = i + 2
            depth = 1
            while j < n and depth > 0:
                if raw.startswith("[[", j):
                    depth += 1
                    j += 2
                elif raw.startswith("]]", j):
                    depth -= 1
                    if depth == 0:
                        break
                    j += 2
                else:
                    j += 1
            if depth != 0:
                buf.append(raw[i:])
                break
            if buf:
                out.append({"t": "x", "s": "".join(buf)})
                buf.clear()
            inner = raw[i + 2 : j]
            if m := re.match(r"^struck:\s?([\s\S]*)$", inner):
                out.append({"t": "st", "c": parse_markup(m.group(1))})
            elif m := re.match(r"^ins:\s?([\s\S]*)$", inner):
                out.append({"t": "in", "c": parse_markup(m.group(1))})
            elif inner.strip() == "?":
                out.append({"t": "ill"})
            elif m := re.match(r"^\?\s+([\s\S]*)$", inner):
                out.append({"t": "gs", "c": parse_markup(m.group(1))})
            elif inner.startswith("quoted passage:"):
                out.append({"t": "q"})
            else:
                out.append({"t": "x", "s": inner})
            i = j + 2
        else:
            buf.append(raw[i])
            i += 1
    if buf:
        out.append({"t": "x", "s": "".join(buf)})
    return out


def _render_clean(nodes: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for node in nodes:
        t = node["t"]
        if t == "x":
            parts.append(node["s"])
        elif t in ("in", "gs"):
            parts.append(" " + _render_clean(node["c"]) + " ")
        elif t == "ill":
            parts.append(" ")
    joined = re.sub(r"\s+", " ", "".join(parts))
    joined = re.sub(r"\s+([,.;:!?])", r"\1", joined)
    return joined.strip()


def _render_auth(nodes: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for node in nodes:
        t = node["t"]
        if t == "x":
            parts.append(node["s"])
        elif t == "ill":
            parts.append(" ")
        elif "c" in node:
            parts.append(" " + _render_auth(node["c"]) + " ")
    joined = re.sub(r"\s+", " ", "".join(parts))
    joined = re.sub(r"\s+([,.;:!?])", r"\1", joined)
    return joined.strip()


def clean_and_auth_text(raw: str) -> tuple[str, str]:
    """Return (clean_text, auth_text) for a raw j.json line."""
    nodes = parse_markup(raw)
    return _render_clean(nodes), _render_auth(nodes)


def normalize_text(text: str) -> tuple[str, list[str]]:
    """Normalize text to space-joined lowercase alphanumeric string + token list."""
    s = unicodedata.normalize("NFKC", text).lower()
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    for sep in ("\u2013", "\u2014", "-", "/", "\u2022", "\u2192", "\u00b7"):
        s = s.replace(sep, " ")
    s = s.replace("'", "")
    tokens = re.findall(r"[a-z0-9]+", s)
    return " ".join(tokens), tokens


def build_corpus_index(j_json_path: Path) -> CorpusIndex:
    """Load site/data/j.json and index all pieces and versions."""
    data = json.loads(j_json_path.read_text(encoding="utf-8"))
    pages_by_id = {p["id"]: p for p in data["pages"]}
    accepted = data.get("acceptedReadings") or {}

    versions: list[VersionIndex] = []
    piece_tokens_map: dict[str, set[str]] = {}
    piece_previews: dict[str, str] = {}

    for piece in data["pieces"]:
        piece_id = piece["id"]
        piece_tokens_map.setdefault(piece_id, set())

        for version in piece["V"]:
            version_id = version["id"]
            clean_lines: list[str] = []
            auth_lines: list[str] = []

            for page_id, block_indices in version["P"]:
                page = pages_by_id[page_id]
                blocks = page["B"]
                for bi in block_indices:
                    block = blocks[bi]
                    if block.get("t") == 4 or not block.get("L"):
                        continue
                    line_ids = block.get("lineIds")
                    for li, raw_line in enumerate(block["L"]):
                        if isinstance(line_ids, list) and li < len(line_ids):
                            line_id = line_ids[li]
                        else:
                            line_id = f"{page_id}-{bi}-{li}"
                        override = accepted.get(line_id)
                        effective = override if isinstance(override, str) else raw_line
                        c_line, a_line = clean_and_auth_text(effective)
                        if c_line:
                            clean_lines.append(c_line)
                        if a_line:
                            auth_lines.append(a_line)

            clean_raw = "\n".join(clean_lines)
            auth_raw = "\n".join(auth_lines)
            clean_norm, clean_tokens = normalize_text(clean_raw)
            auth_norm, auth_tokens = normalize_text(auth_raw)
            preview = clean_lines[0] if clean_lines else (auth_lines[0] if auth_lines else "")

            if piece_id not in piece_previews and preview:
                piece_previews[piece_id] = preview

            clean_set = frozenset(clean_tokens)
            auth_set = frozenset(auth_tokens)
            piece_tokens_map[piece_id].update(clean_set)
            piece_tokens_map[piece_id].update(auth_set)

            versions.append(
                VersionIndex(
                    piece_id=piece_id,
                    version_id=version_id,
                    clean_norm=clean_norm,
                    clean_tokens=tuple(clean_tokens),
                    clean_set=clean_set,
                    auth_norm=auth_norm,
                    auth_tokens=tuple(auth_tokens),
                    auth_set=auth_set,
                    preview=preview,
                )
            )

    n_pieces = len(data["pieces"])
    df: dict[str, int] = {}
    for toks in piece_tokens_map.values():
        for tok in toks:
            df[tok] = df.get(tok, 0) + 1
    idf = {tok: math.log((n_pieces + 1) / (count + 1)) + 1.0 for tok, count in df.items()}

    return CorpusIndex(
        versions=tuple(versions),
        idf=idf,
        pieces_count=n_pieces,
        versions_count=len(versions),
        piece_previews=piece_previews,
    )


def _score_variant(
    q_norm: str,
    q_tokens: list[str],
    q_set: frozenset[str],
    d_norm: str,
    d_tokens: tuple[str, ...],
    d_set: frozenset[str],
    idf: dict[str, float],
) -> tuple[float, float, float]:
    if not q_tokens or not d_tokens:
        return 0.0, 0.0, 0.0

    inter = q_set & d_set
    if not inter:
        token_overlap = 0.0
    else:
        w_inter = sum(idf.get(t, 1.0) for t in inter)
        w_q = sum(idf.get(t, 1.0) for t in q_set)
        w_d = sum(idf.get(t, 1.0) for t in d_set)
        dice = (2.0 * w_inter) / (w_q + w_d) if (w_q + w_d) > 0.0 else 0.0
        conf = min(1.0, len(inter) / 4.0)
        contain = conf * 0.85 * max(w_inter / w_q, w_inter / w_d)
        token_overlap = min(1.0, max(dice, contain))

    wr = fuzz.WRatio(q_norm, d_norm) / 100.0
    tsr = fuzz.token_set_ratio(q_norm, d_norm) / 100.0
    pr = fuzz.partial_ratio(q_norm, d_norm) / 100.0
    rt = fuzz.ratio(q_norm, d_norm) / 100.0

    min_len = min(len(q_tokens), len(d_tokens))
    if min_len >= 4:
        fuzzy_score = 0.50 * wr + 0.30 * tsr + 0.20 * pr
    else:
        damping = min_len / 4.0
        fuzzy_score = 0.55 * wr + 0.25 * rt + 0.20 * damping * max(tsr, pr)

    score = 0.45 * token_overlap + 0.55 * fuzzy_score
    return score, token_overlap, fuzzy_score


def score_query(query_text: str, corpus: CorpusIndex, top_k: int = 3) -> list[dict[str, Any]]:
    """Score query_text against all indexed versions and return top-k unique pieces."""
    if fuzz is None:
        raise RuntimeError(
            "rapidfuzz is required for scoring; run 'python3 tools/bootstrap_env.py' or use .venv/bin/python"
        )
    q_norm, q_tokens = normalize_text(query_text)
    if not q_tokens:
        return []
    q_set = frozenset(q_tokens)

    best_by_piece: dict[str, tuple[float, float, float]] = {}
    for ver in corpus.versions:
        c_scores = _score_variant(
            q_norm, q_tokens, q_set, ver.clean_norm, ver.clean_tokens, ver.clean_set, corpus.idf
        )
        best_v = c_scores
        if ver.auth_norm != ver.clean_norm:
            a_scores = _score_variant(
                q_norm, q_tokens, q_set, ver.auth_norm, ver.auth_tokens, ver.auth_set, corpus.idf
            )
            if a_scores > best_v:
                best_v = a_scores

        prev = best_by_piece.get(ver.piece_id)
        if prev is None or best_v > prev:
            best_by_piece[ver.piece_id] = best_v

    ranked = []
    for piece_id, (score, overlap, fuzzy) in best_by_piece.items():
        if score <= 0.0:
            continue
        ranked.append(
            {
                "piece_id": piece_id,
                "score": round(score, 4),
                "token_overlap": round(overlap, 4),
                "fuzzy_score": round(fuzzy, 4),
            }
        )

    ranked.sort(key=lambda c: (-c["score"], -c["token_overlap"], -c["fuzzy_score"], c["piece_id"]))
    return ranked[:top_k]


def classify_bucket(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "unmatched"
    top_score = float(candidates[0].get("score", 0.0))
    if top_score >= HIGH_CONFIDENCE_MIN:
        if len(candidates) == 1 or (top_score - float(candidates[1].get("score", 0.0))) >= HIGH_CONFIDENCE_MARGIN:
            return "high_confidence"
    if top_score >= AMBIGUOUS_MIN:
        return "ambiguous"
    return "unmatched"


def ensure_outside_git_tree(path: Path) -> Path:
    """Refuse any path located inside a git working tree."""
    abs_path = Path(os.path.abspath(os.fspath(path)))
    resolved = path.resolve()
    for candidate_root in (resolved, abs_path):
        for anc in (candidate_root, *candidate_root.parents):
            if (anc / ".git").exists():
                raise ValueError(f"refused to write review report inside git working tree ({anc}): {path}")
    return resolved


def _extract_list_payload(raw: Any, wrapper_keys: tuple[str, ...], label: str) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = None
        for key in wrapper_keys:
            if isinstance(raw.get(key), list):
                items = raw[key]
                break
        if items is None:
            raise ValueError(f"{label} must be a JSON list or an object containing one of {wrapper_keys}")
    else:
        raise ValueError(f"{label} must be a JSON list or wrapped object")
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{label}[{idx}] must be a JSON object")
    return items


def load_photos(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = _extract_list_payload(raw, ("photos", "witnesses", "items"), "photo_witnesses.json")
    photos: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        uuid = item.get("photo_uuid")
        if not isinstance(uuid, str) or not uuid.strip():
            raise ValueError(f"photo_witnesses.json[{idx}] missing non-empty photo_uuid")
        photos.append(
            {
                "photo_uuid": uuid.strip(),
                "photo_sha256": str(item.get("photo_sha256") or ""),
                "witnessed_at": str(item.get("witnessed_at") or ""),
                "camera_model": str(item.get("camera_model") or ""),
                "local_path": str(item.get("local_path") or ""),
            }
        )
    photos.sort(key=lambda p: (p["witnessed_at"], p["photo_uuid"]))
    return photos


def load_notes(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = _extract_list_payload(raw, ("notes", "items"), "ios_notes.json")
    notes: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        note_id = item.get("note_id")
        if not isinstance(note_id, str) or not note_id.strip():
            raise ValueError(f"ios_notes.json[{idx}] missing non-empty note_id")
        plaintext = item.get("plaintext")
        plaintext_str = plaintext if isinstance(plaintext, str) else ""
        digest = item.get("text_sha256")
        if not isinstance(digest, str) or not digest.strip():
            digest = "sha256:" + hashlib.sha256(plaintext_str.encode("utf-8")).hexdigest()
        notes.append(
            {
                "note_id": note_id.strip(),
                "text_sha256": digest,
                "created_at": str(item.get("created_at") or ""),
                "modified_at": str(item.get("modified_at") or ""),
                "plaintext": plaintext_str,
                "title": str(item.get("title") or ""),
                "folder": str(item.get("folder") or ""),
            }
        )
    notes.sort(key=lambda n: (n["created_at"], n["note_id"]))
    return notes


def _extract_ocr_entry_text(entry: Any) -> str:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        text = entry.get("text")
        if isinstance(text, str) and text.strip():
            return text
        lines = entry.get("lines")
        if isinstance(lines, list):
            parts: list[str] = []
            for line in lines:
                if isinstance(line, str):
                    if line:
                        parts.append(line)
                elif isinstance(line, dict):
                    val = line.get("text")
                    if isinstance(val, str) and val:
                        parts.append(val)
            if parts:
                return "\n".join(parts)
        if isinstance(text, str):
            return text
    return ""


def load_ocr_cache(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    if isinstance(raw, dict):
        for uuid, entry in raw.items():
            if isinstance(uuid, str) and uuid:
                out[uuid] = _extract_ocr_entry_text(entry)
        return out
    if isinstance(raw, list):
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValueError(f"ocr_cache.json[{idx}] must be a JSON object")
            uuid = item.get("photo_uuid")
            if isinstance(uuid, str) and uuid:
                out[uuid] = _extract_ocr_entry_text(item)
        return out
    raise ValueError("ocr_cache.json must be a JSON object keyed by photo_uuid or a list of objects")


def run_external_ocr(ocr_cmd: str, intake_dir: Path, ocr_cache_path: Path) -> None:
    """Invoke external OCR command safely with shell=False."""
    tokens = shlex.split(ocr_cmd)
    if not tokens:
        raise ValueError("--ocr-cmd cannot be empty")
    has_placeholder = any("{intake_dir}" in tok or "{ocr_cache}" in tok for tok in tokens)
    cmd = [
        tok.replace("{intake_dir}", str(intake_dir)).replace("{ocr_cache}", str(ocr_cache_path))
        for tok in tokens
    ]
    if not has_placeholder:
        cmd.extend(["--out-dir", str(intake_dir)])
    env = dict(os.environ)
    env["WITNESS_INTAKE_DIR"] = str(intake_dir)
    env["WITNESS_OCR_CACHE"] = str(ocr_cache_path)
    proc = subprocess.run(cmd, shell=False, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"external OCR command failed with exit {proc.returncode}: {detail}")


def _sanitize_candidates(raw_candidates: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_candidates, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for cand in raw_candidates:
        if not isinstance(cand, dict):
            continue
        cleaned.append(
            {
                "piece_id": str(cand.get("piece_id") or ""),
                "score": round(float(cand.get("score", 0.0)), 4),
                "token_overlap": round(float(cand.get("token_overlap", 0.0)), 4),
                "fuzzy_score": round(float(cand.get("fuzzy_score", 0.0)), 4),
            }
        )
    return cleaned


def _is_reviewed_photo(entry: dict[str, Any]) -> bool:
    return (
        entry.get("status", "pending_review") != "pending_review"
        or entry.get("confirmed_piece_id") is not None
        or entry.get("textual_state", "unreviewed") != "unreviewed"
    )


def _is_reviewed_note(entry: dict[str, Any]) -> bool:
    return (
        entry.get("status", "pending_review") != "pending_review"
        or entry.get("confirmed_piece_id") is not None
        or entry.get("relation", "unreviewed") != "unreviewed"
    )


def _allocate_photo_id(
    photo_uuid: str,
    photo_sha256: str,
    existing_by_uuid: dict[str, dict[str, Any]],
    used_ids: set[str],
) -> str:
    prev = existing_by_uuid.get(photo_uuid)
    if prev:
        prev_id = prev.get("photo_id")
        if isinstance(prev_id, str) and prev_id:
            used_ids.add(prev_id)
            return prev_id
    slug = re.sub(r"[^a-z0-9]", "", photo_uuid.lower())[:8]
    if not slug:
        hex_part = photo_sha256.removeprefix("sha256:")
        slug = re.sub(r"[^a-z0-9]", "", hex_part.lower())[:8] or "photo"
    base = f"ph-{slug}"
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def _sanitize_photo_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "photo_id": str(entry.get("photo_id") or ""),
        "photo_uuid": str(entry.get("photo_uuid") or ""),
        "photo_sha256": str(entry.get("photo_sha256") or ""),
        "witnessed_at": str(entry.get("witnessed_at") or ""),
        "camera_model": str(entry.get("camera_model") or ""),
        "candidates": _sanitize_candidates(entry.get("candidates")),
        "confirmed_piece_id": entry.get("confirmed_piece_id"),
        "status": str(entry.get("status") or "pending_review"),
        "textual_state": str(entry.get("textual_state") or "unreviewed"),
    }


def _sanitize_note_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "note_id": str(entry.get("note_id") or ""),
        "text_sha256": str(entry.get("text_sha256") or ""),
        "created_at": str(entry.get("created_at") or ""),
        "modified_at": str(entry.get("modified_at") or ""),
        "candidates": _sanitize_candidates(entry.get("candidates")),
        "confirmed_piece_id": entry.get("confirmed_piece_id"),
        "status": str(entry.get("status") or "pending_review"),
        "relation": str(entry.get("relation") or "unreviewed"),
    }


def validate_public_payload(obj: Any, path: str = "$") -> None:
    """Recursively verify that no forbidden private fields exist in public JSON."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in FORBIDDEN_PUBLIC_KEYS:
                raise ValueError(f"privacy violation: forbidden key {key!r} at {path}")
            validate_public_payload(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            validate_public_payload(item, f"{path}[{idx}]")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def load_existing_links(out_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if not out_path.exists():
        return {}, {}
    raw = json.loads(out_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"existing {out_path} must be a JSON object")
    photo_list = raw.get("photo_links", [])
    note_list = raw.get("note_links", [])
    if not isinstance(photo_list, list) or not isinstance(note_list, list):
        raise ValueError(f"existing {out_path} must have list photo_links and note_links")
    photos_by_uuid: dict[str, dict[str, Any]] = {}
    for entry in photo_list:
        if isinstance(entry, dict) and isinstance(entry.get("photo_uuid"), str):
            photos_by_uuid[entry["photo_uuid"]] = entry
    notes_by_id: dict[str, dict[str, Any]] = {}
    for entry in note_list:
        if isinstance(entry, dict) and isinstance(entry.get("note_id"), str):
            notes_by_id[entry["note_id"]] = entry
    return photos_by_uuid, notes_by_id


def _truncate_snippet(text: str, limit: int = 240) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def render_review_report(
    generated_at: str,
    intake_summary: dict[str, Any],
    photo_records: list[dict[str, Any]],
    note_records: list[dict[str, Any]],
    piece_previews: dict[str, str],
) -> str:
    lines: list[str] = [
        "# Witness Candidate Review Report",
        "",
        f"- Generated: `{generated_at}`",
        f"- Pieces indexed: {intake_summary['pieces_indexed']} ({intake_summary['versions_indexed']} versions)",
        f"- Photos: {intake_summary['photo_count']} ({intake_summary['photos_with_ocr']} with OCR) — "
        f"high_confidence={intake_summary['photo_buckets']['high_confidence']}, "
        f"ambiguous={intake_summary['photo_buckets']['ambiguous']}, "
        f"unmatched={intake_summary['photo_buckets']['unmatched']}",
        f"- Apple Notes: {intake_summary['note_count']} — "
        f"high_confidence={intake_summary['note_buckets']['high_confidence']}, "
        f"ambiguous={intake_summary['note_buckets']['ambiguous']}, "
        f"unmatched={intake_summary['note_buckets']['unmatched']}",
        "",
    ]

    for section_title, records, kind in (
        ("Photos", photo_records, "photo"),
        ("Apple Notes", note_records, "note"),
    ):
        lines.append(f"## {section_title}")
        lines.append("")
        for bucket_key, bucket_label in (
            ("high_confidence", "High Confidence"),
            ("ambiguous", "Ambiguous"),
            ("unmatched", "Unmatched"),
        ):
            bucket_items = [r for r in records if r["bucket"] == bucket_key]
            lines.append(f"### {bucket_label} ({len(bucket_items)})")
            lines.append("")
            if not bucket_items:
                lines.append("_None._")
                lines.append("")
                continue
            for rec in bucket_items:
                entry = rec["entry"]
                if kind == "photo":
                    lines.append(
                        f"- **{entry['photo_id']}** (`{entry['photo_uuid']}`) "
                        f"| `{entry['witnessed_at'] or 'no-timestamp'}` "
                        f"| status=`{entry['status']}` | textual_state=`{entry['textual_state']}`"
                    )
                    if rec["local_path"]:
                        lines.append(f"  - local_path: `{rec['local_path']}`")
                else:
                    lines.append(
                        f"- **{entry['note_id']}** "
                        f"| `{entry['created_at'] or 'no-timestamp'}` "
                        f"| status=`{entry['status']}` | relation=`{entry['relation']}`"
                    )
                    if rec["folder"] or rec["title"]:
                        lines.append(f"  - folder/title: `{rec['folder']}` / `{rec['title']}`")
                snippet = _truncate_snippet(rec["raw_text"])
                lines.append(f"  - snippet: `{snippet}`" if snippet else "  - snippet: _(empty)_")
                cands = entry["candidates"]
                if cands:
                    lines.append("  - candidates:")
                    for cand in cands:
                        preview = _truncate_snippet(piece_previews.get(cand["piece_id"], ""), 100)
                        lines.append(
                            f"    - `{cand['piece_id']}` score={cand['score']:.4f} "
                            f"(overlap={cand['token_overlap']:.4f}, fuzzy={cand['fuzzy_score']:.4f}) "
                            f"— {preview}"
                        )
                else:
                    lines.append("  - candidates: _(none)_")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def format_stdout_summary(
    intake_summary: dict[str, Any],
    photo_records: list[dict[str, Any]],
    note_records: list[dict[str, Any]],
) -> str:
    pb = intake_summary["photo_buckets"]
    nb = intake_summary["note_buckets"]
    lines = [
        f"Indexed {intake_summary['pieces_indexed']} pieces ({intake_summary['versions_indexed']} versions)",
        f"Photos ({intake_summary['photo_count']} total, {intake_summary['photos_with_ocr']} with OCR): "
        f"high_confidence={pb['high_confidence']} ambiguous={pb['ambiguous']} unmatched={pb['unmatched']}",
        f"Notes ({intake_summary['note_count']} total): "
        f"high_confidence={nb['high_confidence']} ambiguous={nb['ambiguous']} unmatched={nb['unmatched']}",
    ]
    for rec in photo_records:
        entry = rec["entry"]
        top = entry["candidates"][0] if entry["candidates"] else None
        top_desc = f"{top['piece_id']} ({top['score']:.4f})" if top else "none"
        lines.append(f"  photo {entry['photo_id']} [{rec['bucket']}] -> {top_desc}")
    for rec in note_records:
        entry = rec["entry"]
        top = entry["candidates"][0] if entry["candidates"] else None
        top_desc = f"{top['piece_id']} ({top['score']:.4f})" if top else "none"
        lines.append(f"  note {entry['note_id']} [{rec['bucket']}] -> {top_desc}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--intake-dir",
        type=Path,
        default=DEFAULT_INTAKE_DIR,
        help=f"External raw intake directory (default: {DEFAULT_INTAKE_DIR})",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "source" / "witness_links.json",
        help="Public-safe output JSON path (default: source/witness_links.json)",
    )
    ap.add_argument(
        "--j-json",
        type=Path,
        default=ROOT / "site" / "data" / "j.json",
        help="Path to site/data/j.json (default: site/data/j.json)",
    )
    ap.add_argument(
        "--run-ocr",
        action="store_true",
        help="Run external --ocr-cmd to populate/refresh <intake-dir>/ocr_cache.json",
    )
    ap.add_argument(
        "--ocr-cmd",
        default=None,
        help="External OCR CLI command (from tool-notes-docs-capture) invoked when --run-ocr is set or ocr_cache.json is missing",
    )
    ap.add_argument(
        "--review-report",
        type=Path,
        default=None,
        help="Verbose Markdown review report path (default: <intake-dir>/witness_review_report.md; must be outside any git repo)",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    intake_dir = args.intake_dir
    out_path = args.out
    j_json_path = args.j_json
    report_path = args.review_report if args.review_report is not None else (intake_dir / "witness_review_report.md")

    if fuzz is None:
        print(
            "error: rapidfuzz is not installed in this Python environment. "
            "Run 'python3 tools/bootstrap_env.py' or invoke with .venv/bin/python.",
            file=sys.stderr,
        )
        return 2

    try:
        safe_report_path = ensure_outside_git_tree(report_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    photo_witnesses_path = intake_dir / "photo_witnesses.json"
    ios_notes_path = intake_dir / "ios_notes.json"
    ocr_cache_path = intake_dir / "ocr_cache.json"

    if not photo_witnesses_path.is_file() and not ios_notes_path.is_file():
        print(
            f"error: neither {photo_witnesses_path} nor {ios_notes_path} exists in intake directory {intake_dir}",
            file=sys.stderr,
        )
        return 2

    if not j_json_path.is_file():
        print(f"error: transcript file not found: {j_json_path}", file=sys.stderr)
        return 2

    if args.run_ocr:
        if not args.ocr_cmd or not args.ocr_cmd.strip():
            print(
                "error: --run-ocr requires --ocr-cmd pointing to the external capture/OCR CLI "
                "(e.g. from tool-notes-docs-capture).",
                file=sys.stderr,
            )
            return 2
        try:
            run_external_ocr(args.ocr_cmd, intake_dir, ocr_cache_path)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    elif args.ocr_cmd and args.ocr_cmd.strip() and not ocr_cache_path.exists():
        try:
            run_external_ocr(args.ocr_cmd, intake_dir, ocr_cache_path)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    try:
        existing_photos, existing_notes = load_existing_links(out_path)
        photos = load_photos(photo_witnesses_path)
        notes = load_notes(ios_notes_path)
        ocr_by_uuid = load_ocr_cache(ocr_cache_path)
        corpus = build_corpus_index(j_json_path)
    except Exception as exc:
        print(f"error: failed to load inputs: {exc}", file=sys.stderr)
        return 2

    used_photo_ids = {
        entry["photo_id"]
        for entry in existing_photos.values()
        if isinstance(entry.get("photo_id"), str) and entry["photo_id"]
    }

    seen_photo_uuids: set[str] = set()
    photo_entries: list[dict[str, Any]] = []
    photo_review_records: list[dict[str, Any]] = []
    photo_buckets = {"high_confidence": 0, "ambiguous": 0, "unmatched": 0}
    photos_with_ocr = 0

    for photo in photos:
        uuid = photo["photo_uuid"]
        seen_photo_uuids.add(uuid)
        ocr_text = ocr_by_uuid.get(uuid, "")
        if ocr_text.strip():
            photos_with_ocr += 1
        computed_candidates = score_query(ocr_text, corpus)

        photo_id = _allocate_photo_id(uuid, photo["photo_sha256"], existing_photos, used_photo_ids)
        prev = existing_photos.get(uuid)
        if prev and _is_reviewed_photo(prev):
            prev_cands = _sanitize_candidates(prev.get("candidates"))
            if prev_cands and prev.get("photo_sha256") == photo["photo_sha256"]:
                candidates = prev_cands
            else:
                candidates = computed_candidates
            entry = {
                "photo_id": photo_id,
                "photo_uuid": uuid,
                "photo_sha256": photo["photo_sha256"] or str(prev.get("photo_sha256") or ""),
                "witnessed_at": photo["witnessed_at"] or str(prev.get("witnessed_at") or ""),
                "camera_model": photo["camera_model"] or str(prev.get("camera_model") or ""),
                "candidates": candidates,
                "confirmed_piece_id": prev.get("confirmed_piece_id"),
                "status": str(prev.get("status") or "pending_review"),
                "textual_state": str(prev.get("textual_state") or "unreviewed"),
            }
        else:
            candidates = computed_candidates
            entry = {
                "photo_id": photo_id,
                "photo_uuid": uuid,
                "photo_sha256": photo["photo_sha256"],
                "witnessed_at": photo["witnessed_at"],
                "camera_model": photo["camera_model"],
                "candidates": candidates,
                "confirmed_piece_id": None,
                "status": "pending_review",
                "textual_state": "unreviewed",
            }

        bucket = classify_bucket(entry["candidates"])
        photo_buckets[bucket] += 1
        photo_entries.append(entry)
        photo_review_records.append(
            {
                "entry": entry,
                "bucket": bucket,
                "raw_text": ocr_text,
                "local_path": photo["local_path"],
            }
        )

    # Preserve reviewed photos absent from the current intake
    for uuid, prev in existing_photos.items():
        if uuid not in seen_photo_uuids and _is_reviewed_photo(prev):
            photo_entries.append(_sanitize_photo_entry(prev))

    photo_entries.sort(key=lambda e: (e["witnessed_at"], e["photo_uuid"]))

    seen_note_ids: set[str] = set()
    note_entries: list[dict[str, Any]] = []
    note_review_records: list[dict[str, Any]] = []
    note_buckets = {"high_confidence": 0, "ambiguous": 0, "unmatched": 0}

    for note in notes:
        note_id = note["note_id"]
        seen_note_ids.add(note_id)
        computed_candidates = score_query(note["plaintext"], corpus)

        prev = existing_notes.get(note_id)
        if prev and _is_reviewed_note(prev):
            prev_cands = _sanitize_candidates(prev.get("candidates"))
            if prev_cands and prev.get("text_sha256") == note["text_sha256"]:
                candidates = prev_cands
            else:
                candidates = computed_candidates
            entry = {
                "note_id": note_id,
                "text_sha256": note["text_sha256"] or str(prev.get("text_sha256") or ""),
                "created_at": note["created_at"] or str(prev.get("created_at") or ""),
                "modified_at": note["modified_at"] or str(prev.get("modified_at") or ""),
                "candidates": candidates,
                "confirmed_piece_id": prev.get("confirmed_piece_id"),
                "status": str(prev.get("status") or "pending_review"),
                "relation": str(prev.get("relation") or "unreviewed"),
            }
        else:
            candidates = computed_candidates
            entry = {
                "note_id": note_id,
                "text_sha256": note["text_sha256"],
                "created_at": note["created_at"],
                "modified_at": note["modified_at"],
                "candidates": candidates,
                "confirmed_piece_id": None,
                "status": "pending_review",
                "relation": "unreviewed",
            }

        bucket = classify_bucket(entry["candidates"])
        note_buckets[bucket] += 1
        note_entries.append(entry)
        note_review_records.append(
            {
                "entry": entry,
                "bucket": bucket,
                "raw_text": note["plaintext"],
                "title": note["title"],
                "folder": note["folder"],
            }
        )

    # Preserve reviewed notes absent from the current intake
    for note_id, prev in existing_notes.items():
        if note_id not in seen_note_ids and _is_reviewed_note(prev):
            note_entries.append(_sanitize_note_entry(prev))

    note_entries.sort(key=lambda e: (e["created_at"], e["note_id"]))

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    intake_summary = {
        "photo_count": len(photos),
        "photos_with_ocr": photos_with_ocr,
        "note_count": len(notes),
        "pieces_indexed": corpus.pieces_count,
        "versions_indexed": corpus.versions_count,
        "photo_buckets": photo_buckets,
        "note_buckets": note_buckets,
    }

    payload = {
        "schema": SCHEMA_VERSION,
        "generated_at": generated_at,
        "intake_summary": intake_summary,
        "photo_links": photo_entries,
        "note_links": note_entries,
    }

    try:
        validate_public_payload(payload)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    atomic_write_text(out_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    report_text = render_review_report(
        generated_at,
        intake_summary,
        photo_review_records,
        note_review_records,
        corpus.piece_previews,
    )
    atomic_write_text(safe_report_path, report_text)

    print(format_stdout_summary(intake_summary, photo_review_records, note_review_records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
