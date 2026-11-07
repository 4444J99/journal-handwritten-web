#!/usr/bin/env python3
"""T09: local, bounded audio acquisition and DSP pilot.

Run with --help. Only NumPy and the Python standard library are required.
Every output is new, private, and explicitly bound to a source manifest.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import wave

import numpy as np

if __package__:
    from . import dsp
else:
    import dsp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
from source_fingerprint import source_binding
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_TAKES = 100
MAX_TOTAL_FRAMES = 48000 * 600
MAX_TAKE_FRAMES = 48000 * 60
MAX_LABELS = 10000
MAX_REQUESTS = 32
MAX_OUTPUT_FRAMES = 48000 * 90
SAMPLE_RATE = 48000
PHONE_SET = set("AA AE AH AO AW AY B CH D DH EH ER EY F G HH IH IY JH K L M N NG OW OY P R S SH T TH UH UW V W Y Z ZH pau dx".split())
MODES = {"forward", "mirror", "red_room", "stretch", "freeze", "octave", "reverb", "source"}
REQUIRED_RECORDING_DECISIONS = ("D01", "D02", "D03", "D10")
DECISIONS = {
    "D01": "reading style", "D02": "carrier phrase", "D03": "pronunciation authority",
    "D04": "vowel split", "D05": "performed material", "D06": "author-written captions",
    "D07": "fallback engine", "D08": "voice licensing", "D09": "raw master privacy",
    "D10": "microphone", "D11": "sound palette", "D12": "struck words",
    "D13": "illegible words", "D14": "iPhone silent-switch behavior",
}
SPEC_PATHS = (
    ("audio:build-spec-2026-10-27", "docs/chats/2026-10-27-custom-synthetic-voice/03-buildout-spec.md"),
    ("audio:research-2026-10-27", "docs/chats/2026-10-27-custom-synthetic-voice/02-voice-bank-research.md"),
    ("audio:research-2026-10-29", "docs/chats/2026-10-29-generative-audio-from-voice/01-voice-audio-research.md"),
    ("audio:implementation-2026-10-29", "docs/chats/2026-10-29-generative-audio-from-voice/02-audio-implementation-plan.md"),
)


class PilotError(Exception):
    def __init__(self, code, message, **context):
        super().__init__(message)
        self.code = code
        self.context = context

    def record(self):
        return {"code": self.code, "message": str(self), **self.context}


def fail(code, message, **context):
    raise PilotError(code, message, **context)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(data)
    return digest.hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def json_float(value):
    number = float(value)
    if not math.isfinite(number):
        fail("nonfinite_json", "JSON floating-point number exceeds the finite range")
    return number


def json_read(path):
    path = Path(path)
    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            fail("json_too_large", "JSON exceeds 2 MiB", file=path.name)
        return json.loads(path.read_text("utf-8"), parse_float=json_float,
                          parse_constant=lambda x: fail("nonfinite_json", f"Nonfinite JSON literal {x}"))
    except PilotError:
        raise
    except (OSError, ValueError, UnicodeError) as exc:
        fail("invalid_json", str(exc), file=path.name)


def safe_output(path):
    path = Path(path).absolute()
    resolved = path.resolve()
    for name in ("site", "studio", "studio-cf", "exports", "release"):
        if resolved.is_relative_to((ROOT / name).resolve()):
            fail("publication_path_forbidden", "Pilot outputs must stay outside deployment/export trees", target=str(path))
    return path


def new_directory(path):
    path = safe_output(path)
    if path.exists() or path.is_symlink():
        fail("output_exists", "Choose a new output directory; existing files are never replaced", target=str(path))
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_bytes(path, data):
    path = safe_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except FileExistsError:
        fail("output_exists", "Existing files are never replaced", target=str(path))


def write_json(path, value):
    write_bytes(path, json_bytes(value))


def require_id(value, name="id"):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}", value):
        fail("invalid_id", f"{name} must be 1–96 safe identifier characters")
    return value


def require_int(value, name, minimum, maximum):
    try:
        return dsp.integer(value, name, minimum, maximum)
    except ValueError as exc:
        fail("invalid_integer", str(exc))


def inside(base, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        fail("unsafe_source_path", "Manifest source paths must be relative")
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        fail("unsafe_source_path", "Manifest source path escapes the session directory")
    if not path.is_file():
        fail("source_missing", "Referenced source is missing", file=relative)
    return path


def runtime():
    return {"python": platform.python_version(), "numpy": np.__version__,
            "platform": platform.system(), "machine": platform.machine(),
            "engine": "t09-calibration-v1",
            "code_sha256": {name: sha256(Path(__file__).parent / name) for name in ("render.py", "dsp.py")}}


def source_refs():
    refs = []
    for identifier, relative in SPEC_PATHS:
        path = ROOT / relative
        if path.is_file():
            refs.append({"id": identifier, "version": "repository-review-2026-11-05",
                         "path": relative, "sha256": sha256(path),
                         "url": f"https://github.com/4444J99/journal-handwritten-web/blob/038d01fb1862f2e569d231b5b3c4c3a4eb1aecda/{relative}"})
    return refs


def read_wav(path, *, fixture, purpose):
    """Read uncompressed PCM without resampling or changing source bytes."""
    path = Path(path)
    try:
        if path.stat().st_size > 10 * 1024 * 1024:
            fail("wav_too_large", "A take is limited to 60 seconds and 10 MiB", file=path.name)
        with wave.open(str(path), "rb") as stream:
            channels, width, rate, frames, comp, _ = stream.getparams()
            if channels != 1 or rate != SAMPLE_RATE or comp != "NONE":
                fail("invalid_wav_format", "Required: uncompressed 48000 Hz mono WAV", file=path.name,
                     actual={"sample_rate": rate, "channels": channels, "compression": comp})
            if width != 3 and not (fixture is True and width == 2):
                fail("invalid_wav_depth", "Human processing masters require PCM24; PCM16 is allowed only for marked fixtures", file=path.name, bits_per_sample=width * 8)
            require_int(frames, "WAV frames", 1, MAX_TAKE_FRAMES)
            raw = stream.readframes(frames)
            if len(raw) != frames * width:
                fail("truncated_wav", "WAV payload is shorter than its header", file=path.name)
    except PilotError:
        raise
    except (OSError, EOFError, wave.Error) as exc:
        fail("invalid_wav", str(exc), file=path.name)
    if width == 2:
        samples = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768
    else:
        values = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        values = values[:, 0] | (values[:, 1] << 8) | (values[:, 2] << 16)
        values = (values ^ 0x800000) - 0x800000
        samples = values.astype(np.float64) / 8388608
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples * samples)))
    peak_dbfs = 20 * math.log10(peak) if peak else None
    rms_dbfs = 20 * math.log10(rms) if rms else None
    if peak >= 10 ** (-1 / 20):
        fail("clipping_or_low_headroom", "Peak reaches the pilot's -1 dBFS rejection threshold", file=path.name, peak_dbfs=peak_dbfs)
    if rms < 1e-5 and purpose != "calibration_room":
        fail("silent_input", "Input is silent or below the pilot's -100 dBFS RMS floor", file=path.name, rms_dbfs=rms_dbfs)
    return samples, {"sample_rate": rate, "channels": channels, "bits_per_sample": width * 8,
                     "frames": frames, "duration_seconds": frames / rate, "peak_dbfs": peak_dbfs,
                     "rms_dbfs": rms_dbfs, "silence_exempt": purpose == "calibration_room"}


def write_wav(path, samples, bits=24):
    samples = dsp.finite_audio(samples)
    if np.max(np.abs(samples)) > 0.999:
        fail("output_clipping", "Refusing to encode clipping output")
    if bits == 16:
        raw = np.rint(samples * 32767).astype("<i2").tobytes()
    elif bits == 24:
        values = np.rint(samples * 8388607).astype(np.int32)
        raw = np.column_stack((values & 255, (values >> 8) & 255, (values >> 16) & 255)).astype(np.uint8).tobytes()
    else:
        fail("invalid_wav_depth", "Output depth must be 16 or 24")
    path = safe_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        with wave.open(output, "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(bits // 8)
            stream.setframerate(SAMPLE_RATE)
            stream.writeframes(raw)


def labels_read(path, frames, take_id, *, fixture, wav_sha256):
    data = json_read(path)
    if not isinstance(data, dict) or data.get("schema_version") != 1 or data.get("take_id") != take_id:
        fail("invalid_labels", "Labels need schema_version=1 and the matching take_id", take_id=take_id)
    if (data.get("wav_sha256") != wav_sha256 or
            type(data.get("wav_frames")) is not int or data["wav_frames"] != frames or
            type(data.get("sample_rate")) is not int or data["sample_rate"] != SAMPLE_RATE):
        fail("alignment_wav_mismatch", "Reviewed labels must identify this exact WAV hash, frame count and sample rate", take_id=take_id)
    if data.get("reviewed") is not True or not isinstance(data.get("reviewer"), str) or not data["reviewer"].strip():
        fail("labels_unreviewed", "Phone boundaries must be explicitly reviewed before cutting", take_id=take_id)
    if data.get("origin") == "technical_fixture_exact" and fixture is not True:
        fail("fixture_labels_for_human", "Synthetic exact labels cannot assert human alignment review", take_id=take_id)
    intervals = data.get("intervals")
    if not isinstance(intervals, list) or not 1 <= len(intervals) <= MAX_LABELS:
        fail("invalid_labels", "Labels require 1–10000 intervals", take_id=take_id)
    prior_end, seen = None, set()
    for label in intervals:
        if not isinstance(label, dict):
            fail("invalid_labels", "Each label must be an object", take_id=take_id)
        identifier = require_id(label.get("id"), "label id")
        if identifier in seen:
            fail("duplicate_label", "Label IDs must be unique per take", take_id=take_id, label_id=identifier)
        seen.add(identifier)
        if label.get("phone") not in PHONE_SET:
            fail("unsupported_phone", "Use an explicit supported unstressed ARPAbet phone, pau, or dx", take_id=take_id, label_id=identifier, phone=label.get("phone"))
        start = require_int(label.get("start_frame"), "start_frame", 0, frames - 1)
        end = require_int(label.get("end_frame"), "end_frame", 1, frames)
        if start >= end:
            fail("invalid_label_range", "Every label needs start_frame < end_frame", take_id=take_id, label_id=identifier)
        if prior_end is not None and prior_end != start:
            fail("label_gap_or_overlap", "Adjacent labels must touch; label intentional gaps as pau", take_id=take_id, label_id=identifier)
        prior_end = end
    return data


def text_phones(text, lexicon, text_source):
    if not isinstance(text, str) or len(text) > 4096:
        fail("invalid_text", "Calibration text must be a string of at most 4096 characters", source=text_source)
    tokens = []
    for raw in text.split():
        token = raw.strip(".,!?;:\"()")
        if not token:
            continue
        if not re.fullmatch(r"[A-Za-z]+(?:['-][A-Za-z]+)*", token):
            fail("unsupported_token", "Token requires an explicit author-approved text/pronunciation treatment", token=raw, source=text_source)
        key = token.casefold()
        if key not in lexicon:
            fail("missing_pronunciation", "No pronunciation exists; no fallback was used", token=token, source=text_source)
        phones = lexicon[key]
        if not isinstance(phones, list) or not phones or any(phone not in PHONE_SET or phone == "pau" for phone in phones):
            fail("invalid_pronunciation", "Lexicon entries require nonempty supported phones; pauses are handled by the renderer", token=token, source=text_source)
        tokens.append((key, phones))
    if not tokens:
        fail("empty_text", "Text contains no supported spoken tokens", source=text_source)
    result = ["pau"]
    for index, (_, phones) in enumerate(tokens):
        if index:
            result.append("pau")
        result.extend(phones)
    result.append("pau")
    if len(result) > 256:
        fail("text_too_long", "Calibration text is limited to 256 phones", source=text_source)
    return result, [token for token, _ in tokens]


def bind_request_source(request, snapshot, line_ids):
    """Attach an explicit v2 source association without changing request text."""
    binding = source_binding(snapshot)
    if not isinstance(line_ids, list) or not line_ids or len(set(line_ids)) != len(line_ids):
        raise ValueError("audio source binding needs distinct explicit line IDs")
    rows = {line["lineId"]: line for line in snapshot["lines"]}
    if any(line_id not in rows for line_id in line_ids):
        raise ValueError("audio source line is not in the exact current version")
    if "text" in request and request["text"] != "\n".join(rows[line_id]["text"] for line_id in line_ids):
        raise ValueError("audio request text differs from its selected effective source lines")
    result = copy.deepcopy(request)
    result["source_binding"] = {**binding, "lineIds": list(line_ids)}
    return result


def current_source_bindings(manifest, *, repo=ROOT, db=None, snapshots=None):
    """Resolve optional request bindings; historical unbound fixtures stay private."""
    from script_realizations import source_snapshot
    snapshots_by_key = {}
    for snapshot in snapshots or []:
        binding = source_binding(snapshot)
        key = (binding["pieceId"], binding["versionId"])
        if key in snapshots_by_key:
            raise ValueError("duplicate current audio source snapshot")
        snapshots_by_key[key] = snapshot
    bindings = {}
    for request in manifest.get("requests", []):
        if "source_binding" not in request:
            continue
        previous = request["source_binding"]
        if not isinstance(previous, dict) or set(previous) != {"pieceId", "versionId", "sourceFingerprint", "lineIds"}:
            raise ValueError("invalid audio source binding")
        key = (previous["pieceId"], previous["versionId"])
        if key not in snapshots_by_key:
            if snapshots is not None:
                raise ValueError("missing current audio source snapshot")
            snapshots_by_key[key] = source_snapshot(repo, *key, db)
        checked = bind_request_source(request, snapshots_by_key[key], previous["lineIds"])["source_binding"]
        if checked != previous:
            raise ValueError("audio source changed; explicit source rebind required")
        bindings[key] = {k: v for k, v in checked.items() if k != "lineIds"}
    return [bindings[key] for key in sorted(bindings)]


def validate_manifest(path, *, snapshot=None, source_repo=ROOT, source_db=None):
    path = Path(path).resolve()
    manifest = json_read(path) if snapshot is None else snapshot
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        fail("invalid_manifest", "Expected a schema_version=1 manifest")
    require_id(manifest.get("session_id"), "session_id")
    fixture = manifest.get("fixture")
    if type(fixture) is not bool:
        fail("invalid_fixture_flag", "fixture must be an explicit boolean")
    if manifest.get("privacy") != {"master": "private", "rendered_release": "undecided", "harness": "local-only"}:
        fail("privacy_gate", "This pilot accepts only private masters, local-only listening and undecided rendered release")
    speaker = manifest.get("speaker")
    if not isinstance(speaker, dict) or not speaker.get("id") or not speaker.get("kind"):
        fail("speaker_missing", "An explicit speaker/source identity is required")
    if fixture and speaker.get("kind") != "synthetic_calibration":
        fail("fixture_identity", "Fixture speaker.kind must be synthetic_calibration")
    if not fixture and speaker.get("kind") != "author_supplied":
        fail("speaker_identity", "Human pilot must identify author_supplied recordings")
    if not isinstance(manifest.get("source_refs"), list) or not manifest["source_refs"]:
        fail("source_refs_missing", "Manifest must retain source/version references")
    takes = manifest.get("takes")
    if not isinstance(takes, list) or not 1 <= len(takes) <= MAX_TAKES:
        fail("invalid_takes", "A session requires 1–100 takes")
    loaded, units, warnings, total_frames = {}, {}, [], 0
    if fixture:
        warnings.append("FIXTURE ONLY: generated tones/noise; no author voice, pronunciation, intelligibility, listening acceptance or alignment accuracy is demonstrated.")
    else:
        decisions = manifest.get("author_decisions", {})
        missing = [key for key in REQUIRED_RECORDING_DECISIONS if not decision_value(decisions, key)]
        if missing:
            fail("recording_decisions_missing", "Record explicit author choices for style, carrier, pronunciation authority and microphone", decision_ids=missing)
        packet_ref = manifest.get("acquisition_packet")
        if not isinstance(packet_ref, dict):
            fail("packet_missing", "Human session must retain its actual decisioned acquisition packet")
        packet_path = inside(path.parent, packet_ref.get("path"))
        if sha256(packet_path) != packet_ref.get("sha256"):
            fail("packet_hash_mismatch", "Acquisition packet hash does not match the manifest")
        packet_data = json_read(packet_path)
        if packet_data.get("author_decisions") != decisions or packet_data.get("packet_id") != packet_ref.get("id"):
            fail("packet_decision_mismatch", "Session decisions and packet identity must match the captured packet")
    for take in takes:
        if not isinstance(take, dict):
            fail("invalid_take", "Each take must be an object")
        identifier = require_id(take.get("id"), "take id")
        if identifier in loaded:
            fail("duplicate_take", "Take IDs must be unique", take_id=identifier)
        if take.get("fixture") is not fixture:
            fail("fixture_mismatch", "Every take must agree with the session's fixture flag", take_id=identifier)
        if not isinstance(take.get("source"), dict) or not take["source"].get("id") or not take["source"].get("version"):
            fail("take_source_missing", "Each take requires a source id and version", take_id=identifier)
        wav_path = inside(path.parent, take.get("path"))
        if sha256(wav_path) != take.get("sha256"):
            fail("source_hash_mismatch", "Raw WAV hash does not match the manifest", take_id=identifier)
        samples, stats = read_wav(wav_path, fixture=fixture, purpose=take.get("purpose"))
        if take.get("audio") != stats:
            fail("audio_metadata_mismatch", "Declared WAV metadata/quality differs from the input", take_id=identifier)
        total_frames += len(samples)
        if total_frames > MAX_TOTAL_FRAMES:
            fail("session_too_large", "Total decoded session exceeds ten minutes")
        label_path = inside(path.parent, take.get("alignment", {}).get("path"))
        if sha256(label_path) != take.get("alignment", {}).get("sha256"):
            fail("alignment_hash_mismatch", "Reviewed alignment hash does not match the manifest", take_id=identifier)
        labels = labels_read(label_path, len(samples), identifier, fixture=fixture, wav_sha256=take["sha256"])
        loaded[identifier] = {"take": take, "samples": samples, "labels": labels, "raw_path": wav_path, "alignment_path": label_path}
        if labels["intervals"][0]["start_frame"] != 0 or labels["intervals"][-1]["end_frame"] != len(samples):
            warnings.append(f"{identifier}: unlabelled leading/trailing frames are excluded from unit selection.")
        if take.get("purpose") == "calibration_room":
            warnings.append(f"{identifier}: room reference retained; RMS alone cannot certify recording noise floor for voiced takes.")
            continue
        for left, right in zip(labels["intervals"], labels["intervals"][1:]):
            start = (left["start_frame"] + left["end_frame"]) // 2
            end = (right["start_frame"] + right["end_frame"]) // 2
            if end - start < 32:
                fail("unit_too_short", "A diphone needs at least 32 frames", take_id=identifier)
            key = f"{left['phone']}-{right['phone']}"
            reference = {"take_id": identifier, "raw_sha256": take["sha256"],
                         "alignment_sha256": take["alignment"]["sha256"],
                         "source": take["source"], "left_label_id": left["id"], "right_label_id": right["id"],
                         "start_frame": start, "mid_frame": left["end_frame"], "end_frame": end,
                         "boundary_method": "reviewed adjacent phone intervals; integer midpoints",
                         "reviewer": labels["reviewer"], "review_origin": labels.get("origin", "manual")}
            units.setdefault(key, []).append({"reference": reference, "samples": samples[start:end]})
    requests = manifest.get("requests")
    if not isinstance(requests, list) or not 1 <= len(requests) <= MAX_REQUESTS:
        fail("invalid_requests", "A pilot requires 1–32 explicit listening requests")
    seen = set()
    for request in requests:
        if not isinstance(request, dict):
            fail("invalid_request", "A listening request must be an object")
        identifier = require_id(request.get("id"), "request id")
        if identifier in seen:
            fail("duplicate_request", "Request IDs must be unique")
        seen.add(identifier)
        if request.get("mode") not in MODES:
            fail("unsupported_mode", "Unknown or gated render mode", request_id=identifier, mode=request.get("mode"))
        if not isinstance(request.get("parameters", {}), dict):
            fail("invalid_parameters", "parameters must be an object", request_id=identifier)
        if not isinstance(request.get("source"), dict) or not request["source"].get("id") or not request["source"].get("version"):
            fail("request_source_missing", "Every listening request requires source id and version", request_id=identifier)
        if request["mode"] in ("forward", "mirror", "red_room"):
            phones, _ = text_phones(request.get("text"), manifest.get("lexicon", {}), request["source"])
            if request["source"].get("text_sha256") != hashlib.sha256(request["text"].encode("utf-8")).hexdigest():
                fail("text_hash_mismatch", "Request source hash must match the exact UTF-8 text", request_id=identifier, source=request["source"])
            sequence = list(reversed(phones)) if request["mode"] == "red_room" else phones
            missing = []
            for left, right in zip(sequence, sequence[1:]):
                key = f"{right}-{left}" if request["mode"] == "mirror" else f"{left}-{right}"
                if key not in units:
                    missing.append(key)
            if missing:
                fail("missing_units", "Required diphones are missing; no substitution was used", request_id=identifier, units=sorted(set(missing)), source=request["source"])
        else:
            take_id = request.get("take_id")
            if take_id not in loaded:
                fail("take_missing", "Texture request references an unknown take", request_id=identifier)
            if loaded[take_id]["take"].get("purpose") == "calibration_room":
                fail("room_as_voice", "Room reference is not a voice/texture source", request_id=identifier)
            matches = [x for x in loaded[take_id]["labels"]["intervals"] if x["id"] == request.get("label_id")]
            if len(matches) != 1:
                fail("label_missing", "Texture request requires exactly one reviewed label", request_id=identifier)
    try:
        current_source_bindings(manifest, repo=source_repo, db=source_db)
    except (ValueError, KeyError, TypeError, OSError) as error:
        fail("source_binding_stale", str(error))
    return manifest, loaded, units, warnings


def decision_value(decisions, key):
    """Accept either the finite-sheet map or its explicit list of decision records."""
    if isinstance(decisions, dict):
        value = decisions.get(key)
    elif isinstance(decisions, list):
        value = next((d for d in decisions if isinstance(d, dict) and d.get("id") == key), None)
    else:
        return None
    if not isinstance(value, dict):
        return None
    choice = value.get("choice", value.get("value"))
    author = value.get("author", value.get("authority"))
    source = value.get("source", value.get("source_ref"))
    return choice if all(isinstance(x, str) and x.strip() for x in (choice, author, source)) else None


def concat_render(request, manifest, units):
    mode = request["mode"]
    params = dict(request.get("parameters", {}))
    allowed = {"crossfade_frames", "preview_seconds"}
    if set(params) - allowed:
        fail("unknown_parameter", "Unsupported concatenation parameter", keys=sorted(set(params) - allowed))
    overlap = require_int(params.get("crossfade_frames", 240), "crossfade_frames", 0, 2400)
    cap = dsp.number(params.get("preview_seconds", 6.0), "preview_seconds", 0.02, 6.0)
    phones, tokens = text_phones(request["text"], manifest.get("lexicon", {}), request["source"])
    order = list(reversed(phones)) if mode == "red_room" else phones
    parts, refs = [], []
    for left, right in zip(order, order[1:]):
        key = f"{right}-{left}" if mode == "mirror" else f"{left}-{right}"
        unit = units[key][0]
        parts.append(unit["samples"][::-1] if mode == "mirror" else unit["samples"])
        refs.append({**unit["reference"], "unit_key": key, "requested_transition": f"{left}-{right}",
                     "reversed_within_unit": mode == "mirror", "candidate_count": len(units[key])})
    # Bound the assembly before allocating it, not only its final playback.
    if sum(len(part) for part in parts) > SAMPLE_RATE * 30:
        fail("assembly_too_long", "Concatenation assembly is limited to 30 seconds")
    assembled, spans = dsp.concatenate(parts, overlap)
    implied = len(assembled)
    if mode == "red_room":
        assembled = assembled[::-1].copy()
        spans = [{"start_frame": implied - span["end_frame"], "end_frame": implied - span["start_frame"],
                  "span_before_buffer_reverse": dict(span)} for span in spans]
        for index, span in enumerate(spans):
            span["overlap_before_frames"] = (max(0, spans[index + 1]["end_frame"] - span["start_frame"])
                                               if index + 1 < len(spans) else 0)
        refs = [{**ref, "whole_buffer_reversed": True} for ref in refs]
    samples = assembled[:round(cap * SAMPLE_RATE)]
    timing = [{**span, "source": ref, "audible_in_preview": span["start_frame"] < len(samples)} for span, ref in zip(spans, refs)]
    parameters = {"algorithm": "midpoint-diphone-concatenation-v1", "crossfade_frames": overlap,
                  "join_window": "equal-power", "unit_selection": "first candidate in explicit manifest order",
                  "text_tokens": tokens, "input_phones": phones, "assembly_phones": order,
                  "whole_buffer_reverse": mode == "red_room", "mirror_definition": "reverse(forward[Y-X])" if mode == "mirror" else None,
                  "red_room_rule_profile": "literal phone reversal only; no expansion/prosody rules" if mode == "red_room" else None,
                  "implied_full_duration_seconds": implied / SAMPLE_RATE, "preview_cap_seconds": cap,
                  "preview_truncated": len(samples) < implied, "pitch_marks": False, "td_psola": False}
    return samples, refs, parameters, timing


def texture_render(request, loaded):
    entry = loaded[request["take_id"]]
    label = next(x for x in entry["labels"]["intervals"] if x["id"] == request["label_id"])
    x = entry["samples"][label["start_frame"]:label["end_frame"]]
    mode = request["mode"]
    params = dict(request.get("parameters", {}))
    allowed = {"stretch": {"factor", "window_seconds", "preview_seconds", "seed"},
               "freeze": {"window_seconds", "preview_seconds", "seed"},
               "octave": {"semitones", "preview_seconds"},
               "reverb": {"wet", "decay", "seed", "preview_seconds"},
               "source": {"preview_seconds"}}[mode]
    if set(params) - allowed:
        fail("unknown_parameter", "Unsupported texture parameter", keys=sorted(set(params) - allowed))
    if mode in ("stretch", "freeze"):
        y, parameters = dsp.spectral_texture(x, SAMPLE_RATE, freeze=mode == "freeze", **params)
    elif mode == "octave":
        y, parameters = dsp.octave(x, SAMPLE_RATE, **params)
    elif mode == "reverb":
        y, parameters = dsp.voice_reverb(x, SAMPLE_RATE, **params)
    else:
        cap = dsp.number(params.get("preview_seconds", 6.0), "preview_seconds", 0.02, 6.0)
        y = x[:round(cap * SAMPLE_RATE)].copy()
        parameters = {"algorithm": "reviewed-source-cut-v1", "preview_cap_seconds": cap,
                      "implied_full_duration_seconds": len(x) / SAMPLE_RATE, "preview_truncated": len(y) < len(x)}
    ref = {"take_id": entry["take"]["id"], "raw_sha256": entry["take"]["sha256"],
           "alignment_sha256": entry["take"]["alignment"]["sha256"], "label_id": label["id"],
           "phone": label["phone"], "start_frame": label["start_frame"], "end_frame": label["end_frame"],
           "source": entry["take"]["source"], "reviewer": entry["labels"]["reviewer"],
           "review_origin": entry["labels"].get("origin", "manual")}
    timing = [{"start_frame": 0, "end_frame": len(y), "source": ref,
               "mapping": "source window and DSP parameters; spectral texture is not a word-time alignment"}]
    return y, [ref], parameters, timing


def run(manifest_path, output, *, source_repo=ROOT, source_db=None):
    output = new_directory(output)
    try:
        manifest_path = Path(manifest_path).resolve()
        if manifest_path.stat().st_size > MAX_JSON_BYTES:
            fail("json_too_large", "Manifest exceeds 2 MiB")
        manifest_bytes = manifest_path.read_bytes()
        manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
        try:
            snapshot = json.loads(manifest_bytes.decode("utf-8"), parse_float=json_float,
                                  parse_constant=lambda x: fail("nonfinite_json", f"Nonfinite JSON literal {x}"))
        except (ValueError, UnicodeError) as exc:
            fail("invalid_json", str(exc), file=manifest_path.name)
        manifest, loaded, units, warnings = validate_manifest(manifest_path, snapshot=snapshot, source_repo=source_repo, source_db=source_db)

        def check_sources():
            try:
                current_source_bindings(manifest, repo=source_repo, db=source_db)
            except (ValueError, KeyError, TypeError, OSError) as error:
                fail("source_binding_stale", str(error))
            if sha256(manifest_path) != manifest_hash:
                fail("manifest_changed", "Manifest bytes changed during rendering; use a stable manifest")
            for identifier, entry in loaded.items():
                if sha256(entry["raw_path"]) != entry["take"]["sha256"]:
                    fail("raw_changed", "Raw source bytes changed during processing", take_id=identifier)
                if sha256(entry["alignment_path"]) != entry["take"]["alignment"]["sha256"]:
                    fail("alignment_changed", "Reviewed alignment bytes changed during processing", take_id=identifier)
            if "acquisition_packet" in manifest:
                packet = manifest["acquisition_packet"]
                if sha256(inside(manifest_path.parent, packet["path"])) != packet["sha256"]:
                    fail("packet_changed", "Acquisition packet bytes changed during processing")

        check_sources()
        env = runtime()
        required = manifest.get("reproducibility", {}).get("numpy")
        if required and required != np.__version__:
            fail("numpy_version_mismatch", "Use the manifest's NumPy version for reproducible rendering", expected=required, actual=np.__version__)
        before = {key: sha256(value["raw_path"]) for key, value in loaded.items()}
        rendered, total = [], 0
        # Prepare and validate all requests before writing any successful samples.
        for request in manifest["requests"]:
            try:
                result = concat_render(request, manifest, units) if request["mode"] in ("forward", "mirror", "red_room") else texture_render(request, loaded)
                samples, refs, parameters, timing = result
                samples, finishing = dsp.finish(samples)
            except ValueError as exc:
                fail("invalid_processing_parameter", str(exc), request_id=request["id"])
            total += len(samples)
            if total > MAX_OUTPUT_FRAMES:
                fail("output_budget_exceeded", "Combined listening outputs are limited to 90 seconds")
            rendered.append((request, samples, refs, {**parameters, "finishing": finishing}, timing))
        check_sources()
        after = {key: sha256(value["raw_path"]) for key, value in loaded.items()}
        if after != before:
            fail("raw_changed", "Source bytes changed during processing")
        receipt = {"schema_version": 1, "fixture": manifest["fixture"], "session_id": manifest["session_id"],
                   "manifest_sha256": manifest_hash, "samples": [], "warnings": warnings, "errors": [],
                   "privacy": manifest["privacy"], "source_refs": manifest["source_refs"],
                   "reproducibility": {"environment": env, "raw_sha256_before": before, "raw_sha256_after": after,
                                       "same_environment_replay_required": True,
                                       "cross_platform_bit_identity": "not established"}}
        logical_bindings = current_source_bindings(manifest, repo=source_repo, db=source_db)
        if logical_bindings:
            receipt["source_fingerprint_version"] = 2
            receipt["source_bindings"] = logical_bindings
        for request, samples, refs, parameters, timing in rendered:
            identifier = request["id"]
            wav = output / "samples" / f"{identifier}.wav"
            timing_path = output / "timing" / f"{identifier}.json"
            write_wav(wav, samples)
            write_json(timing_path, {"schema_version": 1, "sample_id": identifier, "mode": request["mode"],
                                     "sample_rate": SAMPLE_RATE, "sample_frames": len(samples),
                                     "manifest_sha256": receipt["manifest_sha256"], "request_source": request["source"],
                                     "parameters": parameters, "segments": timing})
            receipt["samples"].append({"id": identifier, "label": request.get("label", identifier),
                                       "path": f"samples/{identifier}.wav", "sha256": sha256(wav),
                                       "duration_seconds": len(samples) / SAMPLE_RATE, "mode": request["mode"],
                                       "fixture": manifest["fixture"], "source_refs": refs,
                                       "parameters": parameters, "timing_path": f"timing/{identifier}.json",
                                       "timing_sha256": sha256(timing_path)})
        check_sources()
        write_json(output / "receipt.json", receipt)
        files = sorted(p for p in output.rglob("*") if p.is_file())
        write_bytes(output / "SHA256SUMS", "".join(f"{sha256(p)}  {p.relative_to(output).as_posix()}\n" for p in files).encode())
        return {"status": "fixture_complete" if manifest["fixture"] else "pilot_rendered_pending_listening",
                "receipt": str(output / "receipt.json"), "samples": len(receipt["samples"]),
                "audio_milestone": "open_pending_author_listening"}
    except PilotError as exc:
        write_json(output / "diagnostic.json", {"schema_version": 1, "status": "failed", "errors": [exc.record()]})
        raise


def make_take(directory, identifier, samples, phones, *, purpose="concatenative", bits=16, source=None):
    wav = directory / "raw" / f"{identifier}.wav"
    label_file = directory / "alignments" / f"{identifier}.json"
    write_wav(wav, samples, bits)
    intervals = []
    for i, phone in enumerate(phones):
        intervals.append({"id": f"p{i:02d}", "phone": phone,
                          "start_frame": i * len(samples) // len(phones), "end_frame": (i + 1) * len(samples) // len(phones)})
    write_json(label_file, {"schema_version": 1, "take_id": identifier, "reviewed": True,
                            "reviewer": "deterministic fixture generator", "origin": "technical_fixture_exact",
                            "wav_sha256": sha256(wav), "wav_frames": len(samples), "sample_rate": SAMPLE_RATE,
                            "note": "Exact generated intervals, not an alignment accuracy test", "intervals": intervals})
    _, stats = read_wav(wav, fixture=True, purpose=purpose)
    return {"id": identifier, "path": f"raw/{identifier}.wav", "sha256": sha256(wav),
            "audio": stats, "fixture": True, "purpose": purpose,
            "prompt_id": f"fixture:{identifier}", "source": source or {"id": f"fixture:{identifier}", "version": "v1"},
            "alignment": {"path": f"alignments/{identifier}.json", "sha256": sha256(label_file)}}


def fixture(output):
    directory = new_directory(output)
    alphabet = ["pau", "AA", "M", "S"]
    rng = np.random.default_rng(4444)
    takes = []
    frames = 48000
    t = np.arange(frames // 2) / SAMPLE_RATE
    for i, left in enumerate(alphabet):
        for j, right in enumerate(alphabet):
            parts = []
            for side, phone in enumerate((left, right)):
                index = alphabet.index(phone)
                frequency = 130 + index * 97 + (i * 13 + j * 7 + side * 5)
                envelope = np.sin(np.linspace(0, math.pi, len(t))) ** (1 + 0.25 * side)
                carrier = np.sin(2 * math.pi * frequency * t) + 0.22 * np.sin(2 * math.pi * frequency * 2 * t + 0.3)
                amplitude = 0.012 if phone == "pau" else 0.24
                parts.append(amplitude * envelope * (0.85 * carrier + 0.08 * rng.normal(size=len(t))))
            takes.append(make_take(directory, f"pair-{left}-{right}", np.concatenate(parts), [left, right]))
    time = np.arange(SAMPLE_RATE * 2) / SAMPLE_RATE
    source = (0.2 * np.sin(2 * math.pi * 220 * time) + 0.08 * np.sin(2 * math.pi * 440 * time)
              + 0.01 * rng.normal(size=len(time))) * np.sin(np.linspace(0, math.pi, len(time)))
    takes.append(make_take(directory, "texture-source", source, ["AA"], purpose="texture"))
    request_source = {"id": "fixture:calibration-text", "version": "v1",
                      "text_sha256": hashlib.sha256(b"calibration").hexdigest()}
    requests = [{"id": mode, "mode": mode, "text": "calibration", "source": request_source,
                 "label": {"forward": "Forward concatenation", "mirror": "True mirror units", "red_room": "Software Red Room (literal phones)"}[mode] + " — SYNTHETIC FIXTURE",
                 "parameters": {"crossfade_frames": 240, "preview_seconds": 6.0}} for mode in ("forward", "mirror", "red_room")]
    texture_base = {"take_id": "texture-source", "label_id": "p00", "source": {"id": "fixture:texture-source", "version": "v1"}}
    requests.append({**texture_base, "id": "source", "mode": "source", "label": "Dry reference — SYNTHETIC FIXTURE", "parameters": {"preview_seconds": 6.0}})
    for factor in (10, 50, 200):
        for window in (0.25, 1.0):
            identifier = f"stretch-{factor}x-{int(window*1000)}ms"
            requests.append({**texture_base, "id": identifier, "mode": "stretch", "label": f"Spectral stretch {factor}× / {window}s window — SYNTHETIC FIXTURE",
                             "parameters": {"factor": factor, "window_seconds": window, "preview_seconds": 6.0, "seed": 9}})
    for mode, params in (("freeze", {"window_seconds": 0.25, "preview_seconds": 6.0, "seed": 9}),
                         ("octave", {"semitones": -12, "preview_seconds": 6.0}),
                         ("reverb", {"wet": 0.25, "decay": 0.6, "seed": 9, "preview_seconds": 6.0})):
        requests.append({**texture_base, "id": mode, "mode": mode, "label": f"{mode.capitalize()} — SYNTHETIC FIXTURE", "parameters": params})
    manifest = {"schema_version": 1, "session_id": "t09-fixture-v1", "fixture": True,
                "speaker": {"id": "fixture:tones-and-noise", "kind": "synthetic_calibration", "author_voice": False},
                "privacy": {"master": "private", "rendered_release": "undecided", "harness": "local-only"},
                "author_decisions": {key: {"choice": None, "author": None, "source": None} for key in DECISIONS},
                "source_refs": [{"id": "fixture:generator", "version": "v1", "seed": 4444,
                                 "description": "Deterministic tones/noise. Phone symbols are synthetic plumbing labels only."}] + source_refs(),
                "takes": takes, "lexicon": {"calibration": ["AA", "M", "S"]}, "requests": requests,
                "reproducibility": {"numpy": np.__version__, "generator_environment": runtime()},
                "status": "fixture_only_not_a_voice_bank", "full_bank_approved": False, "listening_approved": False}
    write_json(directory / "session.json", manifest)
    write_bytes(directory / "README.txt", b"SYNTHETIC FIXTURE ONLY: these tones/noise contain no author voice.\nRaw files are immutable generator outputs. Do not publish them.\nRun render.py run --manifest session.json --out a-new-listening-directory.\n")
    return {"status": "fixture_prepared", "manifest": str(directory / "session.json"), "manifest_sha256": sha256(directory / "session.json"), "takes": len(takes)}


def prompt_packet():
    prompts = [
        {"id": "C01", "section": "calibration", "label": "Room reference", "instruction": "Keep the selected microphone, gain and position fixed. Record ten seconds of the room without speaking. Leave all denoising and automatic gain control off when the device allows it.", "target": {"phones": ["pau"], "respelling": "No speech; room sound only"}, "take_number": 1, "estimated_seconds": 20, "requires_decisions": ["D10"]},
        {"id": "C02", "section": "calibration", "label": "Voice level/reference", "instruction": "After choosing reading style and pronunciation reference, say the technical words 'one two three', then sustain the chosen AA vowel comfortably for two seconds. This is a level and session reference, not a performance instruction. Use a tuner only to document the pitch you naturally choose; no target pitch is prescribed.", "target": {"phones": None, "respelling": "one, two, three; then a comfortable 'ah' as defined by your chosen pronunciation reference"}, "take_number": 1, "estimated_seconds": 40, "requires_decisions": ["D01", "D03", "D10"]},
    ]
    chains = [
        (["AA", "M", "AA"], "ah — lips-closed hum — ah"), (["M", "AA", "M"], "hum — ah — hum"),
        (["AA", "S", "AA"], "ah — s hiss — ah"), (["S", "AA", "S"], "s hiss — ah — s hiss"),
        (["IY", "M", "IY"], "ee — hum — ee"), (["M", "IY", "M"], "hum — ee — hum"),
        (["UW", "M", "UW"], "oo — hum — oo"), (["M", "UW", "M"], "hum — oo — hum"),
        (["ER", "M", "ER"], "er — hum — er (rhotic quality needs your reference)"), (["M", "ER", "M"], "hum — er — hum"),
        (["AH", "M", "AH"], "uh — hum — uh"), (["M", "AH", "M"], "hum — uh — hum"),
        (["AA", "N", "AA"], "ah — n hum with tongue at the upper gum ridge — ah"), (["N", "AA", "N"], "n hum — ah — n hum"),
        (["IY", "S", "IY"], "ee — s hiss — ee"), (["S", "IY", "S"], "s hiss — ee — s hiss"),
        (["UW", "SH", "UW"], "oo — sh hiss — oo"), (["SH", "UW", "SH"], "sh hiss — oo — sh hiss"),
        (["AA", "F", "AA"], "ah — f air through lower lip/upper teeth — ah"), (["F", "AA", "F"], "f air — ah — f air"),
        (["AA", "M", "S", "AA"], "ah — hum — s hiss — ah"), (["AA", "S", "M", "AA"], "ah — s hiss — hum — ah"),
        (["IY", "N", "AH"], "ee — n hum — uh"), (["AH", "N", "IY"], "uh — n hum — ee"),
    ]
    for index, (phones, respelling) in enumerate(chains, 3):
        prompts.append({"id": f"C{index:02d}", "section": "concatenative", "label": "Technical transition chain " + " ".join(phones),
                        "instruction": "Read this short calibration chain once in the author-selected style and carrier (or explicitly selected no carrier). Keep transitions connected, with a short pause before and after. The respelling is an aid, not a pronunciation authority; confirm it against D03. Repeat only for a slip or overload.",
                        "target": {"phones": phones, "respelling": respelling}, "take_number": 1,
                        "estimated_seconds": 25, "requires_decisions": ["D01", "D02", "D03", "D10"]})
    categories = [("IY", "ee vowel", "Sustain the selected ee vowel comfortably for about three seconds."),
                  ("AA", "ah vowel", "Sustain the selected ah vowel comfortably for about three seconds."),
                  ("UW", "oo vowel", "Sustain the selected oo vowel comfortably for about three seconds."),
                  ("ER", "er vowel", "Sustain the selected er vowel comfortably for about three seconds; use the chosen pronunciation reference."),
                  ("AH", "uh vowel", "Sustain the selected uh vowel comfortably for about three seconds."),
                  ("M", "lips-closed hum", "Hum with lips closed comfortably for about three seconds."),
                  ("N", "n hum", "Sustain an n hum with the tongue at the upper gum ridge comfortably for about three seconds."),
                  ("S", "s hiss", "Make an unvoiced s hiss comfortably for about three seconds."),
                  ("SH", "sh hiss", "Make an unvoiced sh hiss comfortably for about three seconds."),
                  ("F", "f air", "Sustain comfortable unvoiced f air for about three seconds."),
                  ("breath", "breath", "Record one ordinary comfortable outward breath; do not force duration or breath pressure."),
                  ("whisper", "whisper", "Whisper the technical calibration words 'one two three' once, comfortably. No expressive performance is requested.")]
    for category, respelling, instruction in categories:
        for take_number in (1, 2):
            index = len(prompts) + 1
            prompts.append({"id": f"C{index:02d}", "section": "texture", "label": f"{respelling} / take {take_number}",
                            "instruction": instruction + " Leave a short quiet margin on each side.",
                            "target": {"category": category, "phones": [category] if category in PHONE_SET else None,
                                       "respelling": respelling}, "take_number": take_number, "estimated_seconds": 25,
                            "requires_decisions": ["D01", "D03", "D10"]})
    for prompt in prompts:
        prompt["filename"] = prompt["id"] + ".wav"
        prompt["alignment_filename"] = prompt["id"] + ".json"
    assert len(prompts) == 50
    return {"schema_version": 1, "packet_id": "t09-combined-pilot-v1", "fixture": False,
            "status": "proposed_acquisition_pending_author_choices", "session_minutes": 30,
            "recording_request": {"total_prompts": 50, "calibration": 2, "concatenative": 24, "texture": 24,
                                  "prompt_time_seconds": sum(x["estimated_seconds"] for x in prompts),
                                  "setup_break_label_budget_seconds": 540,
                                  "rule": "One combined pilot, replacing the earlier alternatives; stop at 30 minutes and log omissions. No full bank or performed supplements."},
            "author_decisions": {key: {"topic": title, "choice": None, "author": None, "source": None} for key, title in DECISIONS.items()},
            "prompts": prompts,
            "notes": ["Technical calibration only; no journal text or invented poetry.",
                      "Respellings are provisional aids until the author chooses a pronunciation authority.",
                      "Breath and whisper are texture categories, not extra ARPAbet phones. Their reviewed intervals may use HH or another explicitly chosen supported label; retain the category in take metadata.",
                      "No carrier phrase, reading style, vowel split, performance, palette or release choice has been selected."]}


def packet(output):
    directory = new_directory(output)
    data = prompt_packet()
    write_json(directory / "prompts.json", data)
    lines = ["# T09 combined recording packet", "", "PROPOSAL — 50 prompts total, up to 30 minutes. Complete D01/D02/D03/D10 first.",
             "", "Choose a dry, comfortable setup. Record 48000 Hz, mono, PCM24 WAV processing masters; preserve every original capture. If your device records another format, retain it and make a separately documented conversion. Upconversion adds no fidelity.",
             "", "Save takes as C01.wav through C50.wav. The session accepts an explicitly chosen subset when the timebox ends. Review boundaries before cutting. Nothing is uploaded.", ""]
    for prompt in data["prompts"]:
        lines.extend([f"## {prompt['id']} — {prompt['label']}", "", prompt["instruction"], "", f"Guide: {prompt['target']['respelling']}", "", f"File: `{prompt['filename']}` · reviewed labels: `{prompt['alignment_filename']}`", ""])
    write_bytes(directory / "recording-script.md", "\n".join(lines).encode("utf-8"))
    config = {"schema_version": 1, "session_id": "t09-author-pilot-01", "speaker_id": "author-4444j99",
              "packet_path": "prompts.json",
              "recordings_directory": "/absolute/private/original-wavs", "labels_directory": "/absolute/private/reviewed-labels",
              "take_ids": [], "author_decisions": data["author_decisions"],
              "source_refs": [{"id": "calibration:t09-combined-pilot", "version": "v1", "packet_sha256": sha256(directory / "prompts.json")}],
              "lexicon": {"calibration": ["AA", "M", "AA"]},
              "requests": [{"id": "dry-reference", "mode": "source", "take_id": "C27", "label_id": "p01",
                            "label": "Private technical reference — awaiting author listening",
                            "source": {"id": "calibration:C27", "version": "take-1"}, "parameters": {"preview_seconds": 6.0}}],
              "notes": "Choose take_ids and request label IDs from your actual reviewed labels. Example request does not assert a take exists."}
    write_json(directory / "session-request.template.json", config)
    write_bytes(directory / "README.txt", b"Read recording-script.md and the repository recording/README.md.\nFill only the required pre-record choices, record, then supply reviewed JSON or import long-format TextGrid.\ninit-session --config session-request.template.json --out a-new-private-session\nrun --manifest that-session/session.json --out a-new-private-listening-directory\n")
    return {"status": "recording_packet_prepared", "prompts": len(data["prompts"]), "directory": str(directory), "recording_authorization": "pending explicit author choices"}


def init_session(config_path, output):
    config_path = Path(config_path).resolve()
    config = json_read(config_path)
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        fail("invalid_config", "Session configuration requires schema_version=1")
    decisions = config.get("author_decisions", {})
    missing = [key for key in REQUIRED_RECORDING_DECISIONS if not decision_value(decisions, key)]
    if missing:
        fail("recording_decisions_missing", "Explicit author style, carrier, pronunciation authority and microphone choices are required", decision_ids=missing)
    packet_name = config.get("packet_path")
    if not isinstance(packet_name, str) or not packet_name.strip():
        fail("packet_missing", "Set packet_path to the actual decisioned prompts.json")
    packet_path = (config_path.parent / packet_name).resolve()
    packet_data = json_read(packet_path)
    packet_hash = sha256(packet_path)
    if not isinstance(packet_data, dict) or packet_data.get("schema_version") != 1 or not isinstance(packet_data.get("prompts"), list):
        fail("invalid_packet", "Packet must contain schema_version=1 and actual prompts")
    if packet_data.get("author_decisions") != decisions:
        fail("packet_decision_mismatch", "Copy the same author decisions into the packet and session configuration")
    if not any(isinstance(ref, dict) and ref.get("packet_sha256") == packet_hash for ref in config.get("source_refs", [])):
        fail("packet_hash_mismatch", "Configuration source_refs must identify the actual decisioned prompts.json hash")
    prompts = {p["id"]: p for p in packet_data["prompts"]}
    records = config.get("takes")
    if records is None:
        ids = config.get("take_ids")
        if not isinstance(ids, list) or not ids:
            fail("takes_not_selected", "Fill take_ids with the actual recorded prompt IDs; no recordings are requested automatically")
        records = []
        for identifier in ids:
            if identifier not in prompts:
                fail("unknown_prompt", "Unknown prompt ID", take_id=identifier)
            p = prompts[identifier]
            records.append({"id": identifier, "wav": str(Path(config.get("recordings_directory", "")) / p["filename"]),
                            "labels": str(Path(config.get("labels_directory", "")) / p["alignment_filename"]),
                            "prompt_id": identifier, "purpose": "calibration_room" if identifier == "C01" else p["section"],
                            "texture_category": p["target"].get("category"),
                            "source": {"id": f"calibration:{identifier}", "version": f"take-{p['take_number']}",
                                       "packet_sha256": packet_hash, "prompt_snapshot": p}})
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_TAKES:
        fail("invalid_takes", "Provide 1–100 actual recorded takes")
    # Validate originals and choices completely before creating the destination.
    prepared, seen = [], set()
    for record in records:
        identifier = require_id(record.get("id"), "take id")
        if identifier in seen:
            fail("duplicate_take", "Take IDs must be unique", take_id=identifier)
        seen.add(identifier)
        wav = Path(record.get("wav", ""))
        labels = Path(record.get("labels", ""))
        if not wav.is_absolute() or not labels.is_absolute():
            fail("absolute_sources_required", "Config WAV and label paths must be absolute", take_id=identifier)
        _, stats = read_wav(wav, fixture=False, purpose=record.get("purpose"))
        labels_read(labels, stats["frames"], identifier, fixture=False, wav_sha256=sha256(wav))
        prepared.append((record, wav, labels, stats, sha256(wav), sha256(labels)))
    if sum(item[3]["frames"] for item in prepared) > MAX_TOTAL_FRAMES:
        fail("session_too_large", "Total decoded session exceeds ten minutes")
    directory = new_directory(output)
    takes = []
    try:
        packet_dest = directory / "acquisition" / "prompts.json"
        write_bytes(packet_dest, packet_path.read_bytes())
        if sha256(packet_dest) != packet_hash or sha256(packet_path) != packet_hash:
            fail("packet_changed", "Acquisition packet changed during intake")
        for record, wav, labels, stats, raw_hash, label_hash in prepared:
            identifier = record["id"]
            wav_dest = directory / "raw" / f"{identifier}.wav"
            label_dest = directory / "alignments" / f"{identifier}.json"
            write_bytes(wav_dest, wav.read_bytes())
            write_bytes(label_dest, labels.read_bytes())
            if sha256(wav) != raw_hash or sha256(wav_dest) != raw_hash or sha256(labels) != label_hash or sha256(label_dest) != label_hash:
                fail("source_changed_during_copy", "Original or copied source changed during acquisition", take_id=identifier)
            takes.append({"id": identifier, "path": f"raw/{identifier}.wav", "sha256": raw_hash,
                          "audio": stats, "fixture": False, "purpose": record.get("purpose", "concatenative"),
                          "prompt_id": record.get("prompt_id", identifier), "texture_category": record.get("texture_category"),
                          "source": record.get("source", {"id": f"calibration:{identifier}", "version": "take-1"}),
                          "original_filename": wav.name,
                          "conversion": record.get("conversion"),
                          "alignment": {"path": f"alignments/{identifier}.json", "sha256": label_hash}})
        manifest = {"schema_version": 1, "session_id": require_id(config.get("session_id"), "session_id"), "fixture": False,
                    "speaker": {"id": require_id(config.get("speaker_id"), "speaker_id"), "kind": "author_supplied",
                                "identity_basis": "operator-supplied; tool performs no speaker verification"},
                    "privacy": {"master": "private", "rendered_release": "undecided", "harness": "local-only"},
                    "author_decisions": decisions, "source_refs": config.get("source_refs", []) + source_refs(),
                    "acquisition_packet": {"id": packet_data["packet_id"], "path": "acquisition/prompts.json", "sha256": packet_hash},
                    "takes": takes, "lexicon": config.get("lexicon", {}), "requests": config.get("requests", []),
                    "reproducibility": {"numpy": np.__version__, "acquisition_environment": runtime()},
                    "status": "technical_pilot_pending_author_listening", "full_bank_approved": False, "listening_approved": False}
        write_json(directory / "session.json", manifest)
        validate_manifest(directory / "session.json")
        return {"status": "private_session_prepared", "manifest": str(directory / "session.json"), "takes": len(takes), "audio_milestone": "open_pending_author_listening"}
    except PilotError as exc:
        write_json(directory / "diagnostic.json", {"schema_version": 1, "status": "failed", "errors": [exc.record()]})
        raise


def labels_template(wav_path, phones, take_id, output, fixture_flag=False):
    _, stats = read_wav(wav_path, fixture=fixture_flag, purpose="calibration_room")
    symbols = phones.split()
    if not symbols or any(x not in PHONE_SET for x in symbols):
        fail("unsupported_phone", "Supply supported phone symbols; include explicit pau for silent gaps")
    data = {"schema_version": 1, "take_id": require_id(take_id), "reviewed": False, "reviewer": None,
            "origin": "manual", "sample_rate": SAMPLE_RATE, "wav_sha256": sha256(wav_path),
            "wav_frames": stats["frames"], "instructions": "Inspect the waveform and listen. Replace every null with an integer frame boundary, then set reviewed=true and reviewer. Do not divide speech into equal durations.",
            "intervals": [{"id": f"p{i:02d}", "phone": phone, "start_frame": None, "end_frame": None} for i, phone in enumerate(symbols)]}
    write_json(output, data)
    return {"status": "labels_template_unreviewed", "output": str(output)}


def import_textgrid(textgrid_path, wav_path, take_id, reviewer, output, tier="phones", fixture_flag=False):
    _, stats = read_wav(wav_path, fixture=fixture_flag, purpose="calibration_room")
    path = Path(textgrid_path)
    if path.stat().st_size > MAX_JSON_BYTES:
        fail("textgrid_too_large", "TextGrid exceeds 2 MiB")
    text = path.read_text("utf-8-sig")
    if 'ooTextFile' not in text or 'TextGrid' not in text or 'item []:' not in text:
        fail("textgrid_format", "Only Praat long-text TextGrid is supported; export as text, long format")
    selected = []
    for block in re.split(r"\n\s*item \[\d+\]:", text)[1:]:
        name = re.search(r'\bname\s*=\s*"((?:""|[^"])*)"', block)
        kind = re.search(r'\bclass\s*=\s*"([^"]+)"', block)
        if name and name.group(1).replace('""', '"') == tier and kind and kind.group(1) == "IntervalTier":
            selected.append(block)
    if len(selected) != 1:
        fail("textgrid_tier", "Require exactly one IntervalTier with the selected name", tier=tier)
    intervals = []
    pattern = r'intervals \[\d+\]:\s*xmin\s*=\s*([^\s]+)\s*xmax\s*=\s*([^\s]+)\s*text\s*=\s*"((?:""|[^"])*)"'
    for i, (start_text, end_text, phone) in enumerate(re.findall(pattern, selected[0])):
        try:
            start, end = float(start_text), float(end_text)
        except ValueError:
            fail("textgrid_time", "Invalid interval time")
        if not math.isfinite(start) or not math.isfinite(end):
            fail("textgrid_time", "Interval times must be finite")
        phone = phone.replace('""', '"')
        if phone not in PHONE_SET:
            fail("unsupported_phone", "TextGrid labels must be explicit supported phones; label blanks as pau after review", phone=phone)
        a, b = round(start * SAMPLE_RATE), round(end * SAMPLE_RATE)
        intervals.append({"id": f"p{i:02d}", "phone": phone, "start_frame": a, "end_frame": b,
                          "imported_seconds": {"start": start, "end": end},
                          "rounding_error_seconds": {"start": a / SAMPLE_RATE - start, "end": b / SAMPLE_RATE - end}})
    data = {"schema_version": 1, "take_id": require_id(take_id), "reviewed": True,
            "reviewer": reviewer, "origin": "reviewed_praat_long_textgrid",
            "sample_rate": SAMPLE_RATE, "wav_sha256": sha256(wav_path), "wav_frames": stats["frames"],
            "import": {"textgrid_sha256": sha256(path), "tier": tier, "rounding": "nearest integer frame, Python round"},
            "intervals": intervals}
    # Validate through an ephemeral private scratch file before final write.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="t09-label-check-") as tmp:
        temp = Path(tmp) / "labels.json"
        temp.write_bytes(json_bytes(data))
        labels_read(temp, stats["frames"], take_id, fixture=fixture_flag, wav_sha256=sha256(wav_path))
    write_json(output, data)
    return {"status": "reviewed_textgrid_imported", "output": str(output), "intervals": len(intervals), "forced_alignment": "not performed"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("fixture", "packet"):
        command = subs.add_parser(name)
        command.add_argument("--out", required=True)
    command = subs.add_parser("run")
    command.add_argument("--manifest", required=True)
    command.add_argument("--out", required=True)
    command.add_argument("--source-repo", type=Path, default=ROOT)
    command.add_argument("--source-db", type=Path)
    command = subs.add_parser("validate")
    command.add_argument("--manifest", required=True)
    command.add_argument("--report", required=True)
    command.add_argument("--source-repo", type=Path, default=ROOT)
    command.add_argument("--source-db", type=Path)
    command = subs.add_parser("init-session")
    command.add_argument("--config", required=True)
    command.add_argument("--out", required=True)
    command = subs.add_parser("labels-template")
    command.add_argument("--wav", required=True)
    command.add_argument("--phones", required=True)
    command.add_argument("--take-id", required=True)
    command.add_argument("--out", required=True)
    command.add_argument("--fixture", action="store_true")
    command = subs.add_parser("import-textgrid")
    command.add_argument("--textgrid", required=True)
    command.add_argument("--wav", required=True)
    command.add_argument("--take-id", required=True)
    command.add_argument("--reviewer", required=True, help="Name of the person who reviewed every imported boundary; passing this affirms that review")
    command.add_argument("--tier", default="phones")
    command.add_argument("--out", required=True)
    command.add_argument("--fixture", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "fixture":
            result = fixture(args.out)
        elif args.command == "packet":
            result = packet(args.out)
        elif args.command == "run":
            result = run(args.manifest, args.out, source_repo=args.source_repo, source_db=args.source_db)
        elif args.command == "init-session":
            result = init_session(args.config, args.out)
        elif args.command == "labels-template":
            result = labels_template(args.wav, args.phones, args.take_id, args.out, args.fixture)
        elif args.command == "import-textgrid":
            result = import_textgrid(args.textgrid, args.wav, args.take_id, args.reviewer, args.out, args.tier, args.fixture)
        else:
            # Check report path before reading; a report may not overwrite a source.
            report = safe_output(args.report)
            if report.exists() or report.is_symlink():
                fail("output_exists", "Validation report must be a new file", target=str(report))
            try:
                manifest, loaded, units, warnings = validate_manifest(args.manifest, source_repo=args.source_repo, source_db=args.source_db)
                result = {"schema_version": 1, "status": "valid", "fixture": manifest["fixture"],
                          "session_id": manifest["session_id"], "manifest_sha256": sha256(args.manifest),
                          "takes": len(loaded), "unique_diphones": len(units), "warnings": warnings, "errors": []}
            except PilotError as exc:
                write_json(report, {"schema_version": 1, "status": "failed", "errors": [exc.record()]})
                raise
            write_json(report, result)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
        return 0
    except PilotError as exc:
        print(json.dumps({"schema_version": 1, "status": "failed", "errors": [exc.record()]}, sort_keys=True, ensure_ascii=False), file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"schema_version": 1, "status": "failed", "errors": [{"code": "invalid_input", "message": str(exc)}]}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
