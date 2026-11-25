"""Unit and integration tests for tools/match_witnesses.py."""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
J_JSON = ROOT / "site" / "data" / "j.json"
sys.path.insert(0, str(TOOLS))

import match_witnesses as mw  # noqa: E402


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        rc = mw.main(argv)
    return rc, out_buf.getvalue(), err_buf.getvalue()


class TranscriptExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = mw.build_corpus_index(J_JSON)

    def test_indexes_all_126_pieces_and_156_versions(self) -> None:
        self.assertEqual(self.corpus.pieces_count, 126)
        self.assertEqual(self.corpus.versions_count, 156)
        piece_ids = {v.piece_id for v in self.corpus.versions}
        self.assertEqual(len(piece_ids), 126)
        self.assertIn("p001", piece_ids)
        self.assertIn("p126", piece_ids)

    def test_accepted_readings_and_struck_dual_variant_on_real_corpus(self) -> None:
        # diary62a-2-3 overrides raw "towers" -> "were so"; diary62a-2-1 adds [[struck: you've]]
        v62 = [v for v in self.corpus.versions if v.version_id == "p001-diary62a-0"][0]
        self.assertNotIn("towers", v62.clean_set)
        self.assertIn("youve", v62.auth_set)
        self.assertNotIn("youve", v62.clean_set)
        cands = mw.score_query("A beast with no maze to call home", self.corpus)
        self.assertEqual(cands[0]["piece_id"], "p001")
        self.assertEqual(mw.classify_bucket(cands), "high_confidence")

    def test_synthetic_markup_overrides_and_t4_exclusion(self) -> None:
        fixture = {
            "pages": [
                {
                    "id": "pg1",
                    "B": [
                        {"t": 0, "L": ["raw [[struck: old]] [[ins: fresh]] [[?]] [[? guess]] [[quoted passage: skip]]"]},
                        {"t": 4, "L": ["forbidden quotation block words"]},
                        {"t": 0, "lineIds": ["custom-line-id"], "L": ["original line text"]},
                    ],
                },
                {
                    "id": "pg2",
                    "B": [
                        {"t": 0, "L": ["second page continuation line"]},
                    ],
                },
            ],
            "acceptedReadings": {
                "custom-line-id": "accepted [[struck: hidden]] replacement",
            },
            "pieces": [
                {
                    "id": "p001",
                    "V": [
                        {"id": "v1", "P": [["pg1", [0, 1, 2]], ["pg2", [0]]]},
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            j_path = Path(tmp) / "j.json"
            j_path.write_text(json.dumps(fixture), encoding="utf-8")
            corpus = mw.build_corpus_index(j_path)
            self.assertEqual(corpus.pieces_count, 1)
            self.assertEqual(corpus.versions_count, 1)
            ver = corpus.versions[0]
            self.assertIn("fresh", ver.clean_set)
            self.assertIn("guess", ver.clean_set)
            self.assertNotIn("old", ver.clean_set)
            self.assertIn("old", ver.auth_set)
            self.assertNotIn("skip", ver.auth_set)
            self.assertNotIn("forbidden", ver.auth_set)
            self.assertIn("replacement", ver.clean_set)
            self.assertNotIn("original", ver.clean_set)
            self.assertIn("hidden", ver.auth_set)
            self.assertIn("continuation", ver.clean_set)

    def test_multipage_and_multiversion_deduplication(self) -> None:
        # Multi-page p099 tail excerpt matches p099 with unique piece_ids
        p099 = [v for v in self.corpus.versions if v.piece_id == "p099"][0]
        tail_query = " ".join(p099.clean_tokens[-25:])
        cands = mw.score_query(tail_query, self.corpus)
        self.assertEqual(len(cands), 3)
        self.assertEqual(len({c["piece_id"] for c in cands}), 3)
        self.assertEqual(cands[0]["piece_id"], "p099")
        self.assertEqual(mw.classify_bucket(cands), "high_confidence")

        # Divergent short version of multi-version p007 (p007-diary46a-1) still ranks p007 #1
        cands_p007 = mw.score_query("How are you not supposed to love her", self.corpus)
        self.assertEqual(cands_p007[0]["piece_id"], "p007")
        self.assertEqual(len({c["piece_id"] for c in cands_p007}), len(cands_p007))


class ScoringBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = mw.build_corpus_index(J_JSON)

    def test_short_poem_p060_exact_match(self) -> None:
        cands = mw.score_query("pixels of a whole", self.corpus)
        self.assertEqual(cands[0]["piece_id"], "p060")
        self.assertGreaterEqual(cands[0]["score"], 0.99)
        self.assertEqual(mw.classify_bucket(cands), "high_confidence")

    def test_ocr_typo_noise_matches_p020(self) -> None:
        p020 = [v for v in self.corpus.versions if v.piece_id == "p020" and v.version_id == "p020-diary13a-0"][0]
        head = " ".join(p020.clean_tokens[:20])
        noisy = head.replace("e", "c", 2).replace("t", "l", 1) + " artifacts"
        cands = mw.score_query(noisy, self.corpus)
        self.assertEqual(cands[0]["piece_id"], "p020")
        self.assertEqual(mw.classify_bucket(cands), "high_confidence")

    def test_empty_and_unrelated_queries(self) -> None:
        self.assertEqual(mw.score_query("", self.corpus), [])
        self.assertEqual(mw.classify_bucket([]), "unmatched")

        unrelated = mw.score_query("buy milk eggs bread bananas coffee beans detergent", self.corpus)
        self.assertEqual(mw.classify_bucket(unrelated), "unmatched")
        if unrelated:
            self.assertLess(unrelated[0]["score"], 0.40)


class DefensiveLoadingAndOcrHookTests(unittest.TestCase):
    def test_fails_when_both_witness_files_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            out_path = Path(tmp) / "witness_links.json"
            rc, _, err = _run_cli(["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)])
            self.assertNotEqual(rc, 0)
            self.assertIn("photo_witnesses.json", err)

    def test_single_present_file_wrapped_dicts_and_ocr_variants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            out_path = Path(tmp) / "witness_links.json"

            # Only photo_witnesses.json (wrapped dict) + list-shaped ocr_cache.json with lines
            (intake / "photo_witnesses.json").write_text(
                json.dumps(
                    {
                        "photos": [
                            {
                                "photo_uuid": "UUID-NO-OCR",
                                "witnessed_at": "2015-04-01T10:00:00Z",
                                "local_path": "/private/no_ocr.jpg",
                            },
                            {
                                "photo_uuid": "UUID-LINES",
                                "witnessed_at": "2015-04-02T10:00:00Z",
                                "camera_model": "iPhone 6",
                                "photo_sha256": "sha256:1111",
                                "local_path": "/private/lines.jpg",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (intake / "ocr_cache.json").write_text(
                json.dumps(
                    [
                        {
                            "photo_uuid": "UUID-LINES",
                            "lines": [{"text": "pixels of"}, "a whole"],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            rc, stdout, stderr = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)]
            )
            self.assertEqual(rc, 0, stderr)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["intake_summary"]["photo_count"], 2)
            self.assertEqual(data["intake_summary"]["photos_with_ocr"], 1)
            self.assertEqual(data["intake_summary"]["note_count"], 0)
            by_uuid = {p["photo_uuid"]: p for p in data["photo_links"]}
            self.assertEqual(by_uuid["UUID-NO-OCR"]["candidates"], [])
            self.assertEqual(by_uuid["UUID-LINES"]["candidates"][0]["piece_id"], "p060")
            self.assertNotIn("/private/", stdout)

    def test_missing_ocr_cache_and_wrapped_notes_computes_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            out_path = Path(tmp) / "witness_links.json"
            plaintext = "pixels of a whole"
            expected_sha = "sha256:" + hashlib.sha256(plaintext.encode("utf-8")).hexdigest()

            (intake / "photo_witnesses.json").write_text("[]", encoding="utf-8")
            (intake / "ios_notes.json").write_text(
                json.dumps(
                    {
                        "notes": [
                            {
                                "note_id": "note-1",
                                "folder": "Secret Drafts",
                                "title": "Private Title",
                                "created_at": "2015-04-05T12:00:00Z",
                                "modified_at": "2015-04-05T12:05:00Z",
                                "plaintext": plaintext,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            rc, _, stderr = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)]
            )
            self.assertEqual(rc, 0, stderr)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["note_links"][0]["text_sha256"], expected_sha)
            self.assertEqual(data["note_links"][0]["candidates"][0]["piece_id"], "p060")

    def test_corrupt_existing_out_refused_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            (intake / "photo_witnesses.json").write_text("[]", encoding="utf-8")
            out_path = Path(tmp) / "witness_links.json"
            out_path.write_text("{corrupt json", encoding="utf-8")
            rc, _, err = _run_cli(["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)])
            self.assertNotEqual(rc, 0)
            self.assertEqual(out_path.read_text(encoding="utf-8"), "{corrupt json")
            self.assertIn("failed to load inputs", err)

    def test_run_ocr_requires_ocr_cmd_and_honors_cache_presence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            out_path = Path(tmp) / "witness_links.json"
            (intake / "photo_witnesses.json").write_text(
                json.dumps([{"photo_uuid": "ABCD1234-9999", "witnessed_at": "2015-04-03T08:00:00Z"}]),
                encoding="utf-8",
            )

            # 1. --run-ocr without --ocr-cmd fails clearly
            rc, _, err = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON), "--run-ocr"]
            )
            self.assertNotEqual(rc, 0)
            self.assertIn("tool-notes-docs-capture", err)

            # 2. Helper script writes ocr_cache.json and touches a marker
            marker = Path(tmp) / "ocr_invoked.txt"
            hook = Path(tmp) / "mock_ocr.py"
            hook.write_text(
                "import json, os, pathlib, sys\n"
                "intake = pathlib.Path(os.environ['WITNESS_INTAKE_DIR'])\n"
                "marker = pathlib.Path(sys.argv[1])\n"
                "marker.write_text(marker.read_text() + 'x' if marker.exists() else 'x')\n"
                "(intake / 'ocr_cache.json').write_text(json.dumps({'ABCD1234-9999': {'text': 'pixels of a whole'}}))\n",
                encoding="utf-8",
            )
            cmd = f"{sys.executable} {hook} {marker} --out-dir {{intake_dir}}"

            # Missing ocr_cache.json + --ocr-cmd (without --run-ocr) invokes hook
            rc, _, stderr = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON), "--ocr-cmd", cmd]
            )
            self.assertEqual(rc, 0, stderr)
            self.assertEqual(marker.read_text(), "x")
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(data["photo_links"][0]["candidates"][0]["piece_id"], "p060")

            # Existing ocr_cache.json + --ocr-cmd (without --run-ocr) is a no-op for hook
            rc, _, stderr = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON), "--ocr-cmd", cmd]
            )
            self.assertEqual(rc, 0, stderr)
            self.assertEqual(marker.read_text(), "x")

            # --run-ocr forces hook invocation even when ocr_cache.json exists
            rc, _, stderr = _run_cli(
                [
                    "--intake-dir",
                    str(intake),
                    "--out",
                    str(out_path),
                    "--j-json",
                    str(J_JSON),
                    "--run-ocr",
                    "--ocr-cmd",
                    cmd,
                ]
            )
            self.assertEqual(rc, 0, stderr)
            self.assertEqual(marker.read_text(), "xx")


class RerunPreservationAndPrivacyTests(unittest.TestCase):
    def test_rerun_preserves_reviewed_entries_and_photo_id_stability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            out_path = Path(tmp) / "witness_links.json"

            # Initial intake with 2 photos and 2 notes
            (intake / "photo_witnesses.json").write_text(
                json.dumps(
                    [
                        {
                            "photo_uuid": "BBBB1111-0001",
                            "witnessed_at": "2015-04-10T10:00:00Z",
                            "photo_sha256": "sha256:bbb1",
                            "camera_model": "iPhone 5s",
                            "local_path": "/Users/private/Photos/b1.jpg",
                        },
                        {
                            "photo_uuid": "BBBB1111-0002",
                            "witnessed_at": "2015-04-11T10:00:00Z",
                            "photo_sha256": "sha256:bbb2",
                            "camera_model": "iPhone 5s",
                            "local_path": "/Users/private/Photos/b2.jpg",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            (intake / "ocr_cache.json").write_text(
                json.dumps(
                    {
                        "BBBB1111-0001": {"text": "pixels of a whole"},
                        "BBBB1111-0002": {"text": "A beast with no maze to call home"},
                    }
                ),
                encoding="utf-8",
            )
            (intake / "ios_notes.json").write_text(
                json.dumps(
                    [
                        {
                            "note_id": "x-coredata://note-confirmed",
                            "folder": "Private Poems",
                            "title": "Secret Poem Title",
                            "created_at": "2015-04-08T09:00:00Z",
                            "modified_at": "2015-04-08T09:30:00Z",
                            "plaintext": "pixels of a whole",
                        },
                        {
                            "note_id": "x-coredata://note-rejected",
                            "folder": "Private Groceries",
                            "title": "Grocery List",
                            "created_at": "2015-04-09T09:00:00Z",
                            "modified_at": "2015-04-09T09:30:00Z",
                            "plaintext": "buy milk eggs bread",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            rc, _, stderr = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)]
            )
            self.assertEqual(rc, 0, stderr)
            first = json.loads(out_path.read_text(encoding="utf-8"))

            # Verify defaults for new entries and collision suffix on shared 8-char prefix
            photos_1 = {p["photo_uuid"]: p for p in first["photo_links"]}
            self.assertEqual(photos_1["BBBB1111-0001"]["photo_id"], "ph-bbbb1111")
            self.assertEqual(photos_1["BBBB1111-0002"]["photo_id"], "ph-bbbb1111-2")
            for p in first["photo_links"]:
                self.assertEqual(p["status"], "pending_review")
                self.assertIsNone(p["confirmed_piece_id"])
                self.assertEqual(p["textual_state"], "unreviewed")
            for n in first["note_links"]:
                self.assertEqual(n["status"], "pending_review")
                self.assertIsNone(n["confirmed_piece_id"])
                self.assertEqual(n["relation"], "unreviewed")

            # Simulate human review on BBBB1111-0001 (confirmed), BBBB1111-0002 (manual textual_state),
            # note-confirmed (confirmed), note-rejected (rejected)
            for p in first["photo_links"]:
                if p["photo_uuid"] == "BBBB1111-0001":
                    p["status"] = "confirmed"
                    p["confirmed_piece_id"] = "p060"
                    p["textual_state"] = "matches_scan"
                elif p["photo_uuid"] == "BBBB1111-0002":
                    p["textual_state"] = "predates_scan_edits"
            for n in first["note_links"]:
                if n["note_id"] == "x-coredata://note-confirmed":
                    n["status"] = "confirmed"
                    n["confirmed_piece_id"] = "p060"
                    n["relation"] = "parallel_draft"
                elif n["note_id"] == "x-coredata://note-rejected":
                    n["status"] = "rejected"
            out_path.write_text(json.dumps(first, indent=2), encoding="utf-8")

            # Partial re-run: omit BBBB1111-0001 & note-rejected, insert an EARLIER photo AAAA0000-0001, add new note
            (intake / "photo_witnesses.json").write_text(
                json.dumps(
                    [
                        {
                            "photo_uuid": "AAAA0000-0001",
                            "witnessed_at": "2015-03-01T10:00:00Z",
                            "photo_sha256": "sha256:aaa0",
                            "local_path": "/Users/private/Photos/a0.jpg",
                        },
                        {
                            "photo_uuid": "BBBB1111-0002",
                            "witnessed_at": "2015-04-11T10:00:00Z",
                            "photo_sha256": "sha256:bbb2",
                            "camera_model": "iPhone 5s",
                            "local_path": "/Users/private/Photos/b2.jpg",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            (intake / "ios_notes.json").write_text(
                json.dumps(
                    [
                        {
                            "note_id": "x-coredata://note-confirmed",
                            "folder": "Private Poems",
                            "title": "Secret Poem Title",
                            "created_at": "2015-04-08T09:00:00Z",
                            "modified_at": "2015-04-08T09:30:00Z",
                            "plaintext": "pixels of a whole",
                        },
                        {
                            "note_id": "x-coredata://note-new",
                            "folder": "Private Poems",
                            "title": "Brand New Draft",
                            "created_at": "2015-04-12T09:00:00Z",
                            "modified_at": "2015-04-12T09:30:00Z",
                            "plaintext": "How are you not supposed to love her",
                        },
                    ]
                ),
                encoding="utf-8",
            )

            rc, stdout, stderr = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)]
            )
            self.assertEqual(rc, 0, stderr)
            second = json.loads(out_path.read_text(encoding="utf-8"))

            photos_2 = {p["photo_uuid"]: p for p in second["photo_links"]}
            notes_2 = {n["note_id"]: n for n in second["note_links"]}

            # Earlier photo did not shift BBBB1111-0002's photo_id; absent confirmed BBBB1111-0001 preserved
            self.assertEqual(photos_2["AAAA0000-0001"]["photo_id"], "ph-aaaa0000")
            self.assertEqual(photos_2["AAAA0000-0001"]["status"], "pending_review")
            self.assertEqual(photos_2["BBBB1111-0002"]["photo_id"], "ph-bbbb1111-2")
            self.assertEqual(photos_2["BBBB1111-0002"]["textual_state"], "predates_scan_edits")
            self.assertIn("BBBB1111-0001", photos_2)
            self.assertEqual(photos_2["BBBB1111-0001"]["status"], "confirmed")
            self.assertEqual(photos_2["BBBB1111-0001"]["confirmed_piece_id"], "p060")
            self.assertEqual(photos_2["BBBB1111-0001"]["textual_state"], "matches_scan")

            # Reviewed notes (both present and absent) preserved; new note defaults to pending_review/unreviewed
            self.assertEqual(notes_2["x-coredata://note-confirmed"]["status"], "confirmed")
            self.assertEqual(notes_2["x-coredata://note-confirmed"]["relation"], "parallel_draft")
            self.assertIn("x-coredata://note-rejected", notes_2)
            self.assertEqual(notes_2["x-coredata://note-rejected"]["status"], "rejected")
            self.assertEqual(notes_2["x-coredata://note-new"]["status"], "pending_review")
            self.assertEqual(notes_2["x-coredata://note-new"]["relation"], "unreviewed")

            # Strict public privacy hygiene on witness_links.json AND stdout
            out_raw = out_path.read_text(encoding="utf-8")
            for p in second["photo_links"]:
                self.assertEqual(set(p.keys()), set(mw.PHOTO_ALLOWED_KEYS))
            for n in second["note_links"]:
                self.assertEqual(set(n.keys()), set(mw.NOTE_ALLOWED_KEYS))
            for sensitive in (
                "Secret Poem Title",
                "Brand New Draft",
                "Private Poems",
                "How are you not supposed to love her",
                "A beast with no maze to call home",
                "/Users/private/Photos/",
            ):
                self.assertNotIn(sensitive, out_raw)
                self.assertNotIn(sensitive, stdout)

            # Review report written outside git contains snippets, paths, and titles
            report_text = (intake / "witness_review_report.md").read_text(encoding="utf-8")
            self.assertIn("Brand New Draft", report_text)
            self.assertIn("/Users/private/Photos/b2.jpg", report_text)
            self.assertIn("How are you not supposed to love her", report_text)

    def test_review_report_refuses_inside_git_working_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            (intake / "photo_witnesses.json").write_text("[]", encoding="utf-8")
            out_path = Path(tmp) / "witness_links.json"

            for git_marker_is_dir in (True, False):
                repo_dir = Path(tmp) / f"repo_{git_marker_is_dir}"
                repo_dir.mkdir()
                if git_marker_is_dir:
                    (repo_dir / ".git").mkdir()
                else:
                    (repo_dir / ".git").write_text("gitdir: /somewhere\n", encoding="utf-8")
                bad_report = repo_dir / "nested" / "review.md"

                rc, _, err = _run_cli(
                    [
                        "--intake-dir",
                        str(intake),
                        "--out",
                        str(out_path),
                        "--j-json",
                        str(J_JSON),
                        "--review-report",
                        str(bad_report),
                    ]
                )
                self.assertNotEqual(rc, 0)
                self.assertIn("git working tree", err)
                self.assertFalse(bad_report.exists())


if __name__ == "__main__":
    unittest.main()
