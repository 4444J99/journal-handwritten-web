"""Tests for tools/build_chronology.py (Stage 3 chronological amalgamation).

All outputs go to temporary directories; protected repository paths are never
written.  The corpus and canonical manifests are read from the checkout only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build_chronology.py"
J_JSON = ROOT / "site" / "data" / "j.json"
CANONICAL = ROOT / "source" / "canonical.json"

FORBIDDEN_KEYS = (
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
)


def photo_link(
    piece_id: str,
    photo_id: str,
    witnessed_at: str,
    *,
    status: str = "confirmed",
    **extra: Any,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "photo_id": photo_id,
        "photo_uuid": f"uuid-{photo_id}",
        "photo_sha256": "sha256:" + photo_id,
        "witnessed_at": witnessed_at,
        "camera_model": "Apple iPhone 6",
        "candidates": [],
        "confirmed_piece_id": piece_id if status == "confirmed" else None,
        "status": status,
        "textual_state": "matches_scan" if status == "confirmed" else "unreviewed",
    }
    entry.update(extra)
    return entry


def note_link(
    note_id: str,
    created_at: str,
    *,
    piece_id: str | None = None,
    status: str = "confirmed",
    relation: str = "standalone_cohort",
    **extra: Any,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "note_id": note_id,
        "text_sha256": "sha256:" + note_id,
        "created_at": created_at,
        "modified_at": created_at,
        "candidates": [],
        "confirmed_piece_id": piece_id if status == "confirmed" else None,
        "status": status,
        "relation": relation if status == "confirmed" else "unreviewed",
    }
    entry.update(extra)
    return entry


class BuildChronologyTests(unittest.TestCase):
    def run_tool(
        self,
        links: dict[str, Any],
        tmp: str,
        digitized_at: str = "2015-09",
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None, Path]:
        base = Path(tmp)
        links_path = base / "witness_links.json"
        out_path = base / "chronology.json"
        links_path.write_text(json.dumps(links, indent=2), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--links",
                str(links_path),
                "--j-json",
                str(J_JSON),
                "--canonical",
                str(CANONICAL),
                "--out",
                str(out_path),
                "--digitized-at",
                digitized_at,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        data = None
        if out_path.is_file():
            data = json.loads(out_path.read_text(encoding="utf-8"))
        return proc, data, out_path

    def assert_no_private_keys(self, obj: Any, path: str = "$") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                self.assertNotIn(str(key).lower(), FORBIDDEN_KEYS, f"{path}.{key}")
                self.assert_no_private_keys(value, f"{path}.{key}")
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                self.assert_no_private_keys(item, f"{path}[{idx}]")

    def by_piece(self, chronology: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {
            entry["piece_id"]: entry
            for entry in chronology["physical_codex_order"]
        }

    def test_01_empty_links_produce_126_undated_pieces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_01_") as tmp:
            proc, data, _ = self.run_tool(
                {"photo_links": [], "note_links": []}, tmp
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIsNotNone(data)
            assert data is not None
            self.assertEqual(data["schema"], "versforms.chronology.v1")
            self.assertEqual(data["digitized_at"], "2015-09")
            self.assertTrue(data["generated_at"])
            self.assertEqual(len(data["physical_codex_order"]), 126)
            self.assertEqual(
                {e["piece_id"] for e in data["physical_codex_order"]},
                {f"p{i:03d}" for i in range(1, 127)},
            )
            for entry in data["physical_codex_order"]:
                self.assertEqual(entry["chronology"]["date_basis"], "undated")
                self.assertIsNone(entry["chronology"]["est_start"])
                self.assertTrue(
                    entry["chronology"]["amalgamated_sort_key"].startswith("undated#")
                )
            self.assertGreaterEqual(len(data["amalgamated_chronological_order"]), 126)
            self.assert_no_private_keys(data)

    def test_02_photo_anchor_bounds_and_schema(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_02_") as tmp:
            links = {
                "photo_links": [
                    photo_link("p001", "ph-001-a", "2015-01-02T19:42:10-05:00")
                ],
                "note_links": [],
            }
            proc, data, _ = self.run_tool(links, tmp)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            assert data is not None
            entry = self.by_piece(data)["p001"]
            chron = entry["chronology"]
            self.assertEqual(chron["date_basis"], "photo_anchored")
            self.assertEqual(chron["est_start"], "2014-12-29")
            self.assertEqual(chron["est_end"], "2015-01-02")
            self.assertEqual(chron["anchor_prev"], None)
            self.assertIsNone(chron["anchor_next"])
            self.assertTrue(chron["amalgamated_sort_key"].endswith("#p001"))
            witnesses = entry["witnesses"]
            self.assertEqual(witnesses["codex_scan"]["surface_id"], "diary1")
            self.assertFalse(witnesses["codex_scan"]["shared_surface"])
            canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))
            expected_sha = next(
                a["sha256"]
                for a in canonical["assets"]
                if a.get("role") == "preserved-jpeg-master" and a.get("pageId") == "diary1"
            )
            self.assertEqual(witnesses["codex_scan"]["scan_sha256"], expected_sha)
            photo = witnesses["photo_witnesses"][0]
            self.assertEqual(photo["photo_id"], "ph-001-a")
            self.assertEqual(photo["textual_state"], "matches_scan")
            self.assertNotIn("status", photo)
            self.assert_no_private_keys(data)

    def test_03_interpolated_span_between_two_anchors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_03_") as tmp:
            links = {
                "photo_links": [
                    photo_link("p001", "ph-001-a", "2015-01-02T10:00:00-05:00"),
                    photo_link("p126", "ph-126-a", "2015-04-12T10:00:00-04:00"),
                ],
                "note_links": [],
            }
            proc, data, _ = self.run_tool(links, tmp)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            assert data is not None
            pieces = self.by_piece(data)
            self.assertEqual(pieces["p001"]["chronology"]["date_basis"], "photo_anchored")
            self.assertEqual(pieces["p126"]["chronology"]["date_basis"], "photo_anchored")
            interior = pieces["p039"]["chronology"]
            self.assertEqual(interior["date_basis"], "interpolated")
            self.assertEqual(interior["anchor_prev"], "ph-001-a")
            self.assertEqual(interior["anchor_next"], "ph-126-a")
            self.assertEqual(interior["est_start"], "2015-01-02")
            self.assertEqual(interior["est_end"], "2015-04-12")
            self.assertFalse(
                interior["amalgamated_sort_key"].startswith("2015-09"),
                "digitized_at leaked into an interpolated sort key",
            )

    def test_04_head_and_tail_extrapolation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_04_") as tmp:
            links = {
                "photo_links": [
                    photo_link("p039", "ph-039-a", "2015-02-16T10:00:00-05:00"),
                    photo_link("p067", "ph-067-a", "2015-03-06T10:00:00-05:00"),
                ],
                "note_links": [],
            }
            proc, data, _ = self.run_tool(links, tmp)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            assert data is not None
            pieces = self.by_piece(data)
            self.assertEqual(pieces["p001"]["chronology"]["date_basis"], "extrapolated_head")
            self.assertEqual(pieces["p001"]["chronology"]["anchor_next"], "ph-039-a")
            self.assertEqual(pieces["p126"]["chronology"]["date_basis"], "extrapolated_tail")
            self.assertEqual(pieces["p126"]["chronology"]["anchor_prev"], "ph-067-a")
            for pid in ("p001", "p126"):
                self.assertIsNotNone(pieces[pid]["chronology"]["est_start"])
                self.assertFalse(
                    pieces[pid]["chronology"]["amalgamated_sort_key"].startswith("2015-09")
                )

    def test_05_two_clock_invariance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_05_") as tmp:
            links = {
                "photo_links": [
                    photo_link("p001", "ph-001-a", "2015-01-02T10:00:00-05:00"),
                    photo_link("p039", "ph-039-a", "2015-02-16T10:00:00-05:00"),
                    photo_link("p126", "ph-126-a", "2015-04-12T10:00:00-04:00"),
                ],
                "note_links": [],
            }
            proc_a, data_a, _ = self.run_tool(links, tmp, digitized_at="2015-09")
            proc_b, data_b, _ = self.run_tool(links, tmp, digitized_at="2024-06")
            self.assertEqual(proc_a.returncode, 0, proc_a.stderr)
            self.assertEqual(proc_b.returncode, 0, proc_b.stderr)
            assert data_a is not None and data_b is not None
            pieces_a = self.by_piece(data_a)
            pieces_b = self.by_piece(data_b)
            for pid in pieces_a:
                self.assertEqual(
                    pieces_a[pid]["chronology"],
                    pieces_b[pid]["chronology"],
                    f"composition window changed with digitized_at on {pid}",
                )
                self.assertEqual(
                    pieces_a[pid]["witnesses"]["photo_witnesses"],
                    pieces_b[pid]["witnesses"]["photo_witnesses"],
                )
            self.assertEqual(data_a["digitized_at"], "2015-09")
            self.assertEqual(data_b["digitized_at"], "2024-06")

    def test_06_only_confirmed_links_are_consumed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_06_") as tmp:
            links = {
                "photo_links": [
                    photo_link("p001", "ph-confirmed", "2015-01-02T10:00:00-05:00"),
                    photo_link("p039", "ph-pending", "2015-02-16T10:00:00-05:00", status="pending_review"),
                    photo_link("p067", "ph-rejected", "2015-03-06T10:00:00-05:00", status="rejected"),
                ],
                "note_links": [
                    note_link("n-confirmed", "2015-01-01T10:00:00-05:00", piece_id="p001"),
                    note_link("n-pending", "2015-01-02T10:00:00-05:00", status="pending_review"),
                ],
            }
            proc, data, _ = self.run_tool(links, tmp)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            assert data is not None
            pieces = self.by_piece(data)
            self.assertEqual(len(pieces["p001"]["witnesses"]["photo_witnesses"]), 1)
            self.assertEqual(pieces["p001"]["witnesses"]["photo_witnesses"][0]["photo_id"], "ph-confirmed")
            self.assertEqual(pieces["p039"]["witnesses"]["photo_witnesses"], [])
            self.assertEqual(pieces["p067"]["witnesses"]["photo_witnesses"], [])
            self.assertEqual(len(pieces["p001"]["witnesses"]["linked_ios_notes"]), 1)
            self.assertEqual(pieces["p039"]["witnesses"]["linked_ios_notes"], [])
            sort_keys = [e["sort_key"] for e in data["amalgamated_chronological_order"]]
            self.assertFalse(any("n-pending" in key for key in sort_keys))

    def test_07_private_fields_in_links_are_not_propagated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_07_") as tmp:
            links = {
                "photo_links": [
                    photo_link(
                        "p001",
                        "ph-leak",
                        "2015-01-02T10:00:00-05:00",
                        plaintext="SECRET NOTE TEXT",
                        local_path="/Users/example/Private/IMG_1.JPG",
                        ocr_text="RAW OCR DUMP",
                        title="Private diary title",
                        folder="PrivateFolder",
                    )
                ],
                "note_links": [],
            }
            proc, data, out_path = self.run_tool(links, tmp)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            assert data is not None
            raw = out_path.read_text(encoding="utf-8")
            for needle in (
                "SECRET NOTE TEXT",
                "/Users/example/",
                "RAW OCR DUMP",
                "Private diary title",
                "PrivateFolder",
            ):
                self.assertNotIn(needle, raw)
            self.assert_no_private_keys(data)

    def test_08_shared_surface_flags(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_08_") as tmp:
            proc, data, _ = self.run_tool({"photo_links": [], "note_links": []}, tmp)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            assert data is not None
            pieces = self.by_piece(data)
            self.assertTrue(pieces["p001"]["witnesses"]["codex_scan"]["shared_surface"] is False)
            self.assertTrue(pieces["p126"]["witnesses"]["codex_scan"]["shared_surface"] is True)
            self.assertTrue(pieces["p081"]["witnesses"]["codex_scan"]["shared_surface"] is True)
            self.assertEqual(pieces["p126"]["witnesses"]["codex_scan"]["surface_id"], "diary62a")

    def test_09_amalgamated_order_includes_interleaved_notes_and_is_sorted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_09_") as tmp:
            links = {
                "photo_links": [
                    photo_link("p001", "ph-001-a", "2015-01-02T10:00:00-05:00")
                ],
                "note_links": [
                    note_link("note-a", "2015-01-01T23:15:00-05:00", piece_id="p001", relation="parallel_draft"),
                    note_link("note-b", "2015-01-03T01:08:00-05:00", relation="standalone_cohort"),
                ],
            }
            proc, data, _ = self.run_tool(links, tmp)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            assert data is not None
            amalg = data["amalgamated_chronological_order"]
            note_entries = [e for e in amalg if e["entry_type"] == "ios_note"]
            self.assertEqual(len(note_entries), 2)
            by_id = {e["note_id"]: e for e in note_entries}
            self.assertEqual(by_id["note-a"]["piece_id"], "p001")
            self.assertEqual(by_id["note-a"]["relation"], "parallel_draft")
            self.assertIsNone(by_id["note-b"]["piece_id"])
            dated = [
                e["sort_key"]
                for e in amalg
                if not e["sort_key"].startswith("undated#")
            ]
            self.assertEqual(dated, sorted(dated))
            self.assertEqual(len([e for e in amalg if e["entry_type"] == "piece"]), 126)

    def test_10_cli_rejects_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="jhw_chron_10_") as tmp:
            base = Path(tmp)
            proc = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--links",
                    str(base / "missing.json"),
                    "--j-json",
                    str(J_JSON),
                    "--canonical",
                    str(CANONICAL),
                    "--out",
                    str(base / "chronology.json"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("error:", proc.stderr)
            self.assertFalse((base / "chronology.json").exists())


if __name__ == "__main__":
    unittest.main()
