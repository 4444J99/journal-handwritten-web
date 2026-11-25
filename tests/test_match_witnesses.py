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

    def test_unrelated_stopwords_and_english_prose_stay_unmatched(self) -> None:
        adversarial_probes = [
            ("pure_stopwords_120w", ("the of a and in to you is are with for it that was were this be have not on my your " * 6).strip()),
            ("pure_common_words_subset", "the of a and in to you is are with for it that was were this be have not on"),
            ("medium_stopword_note_20w", "You are not supposed to be here in the middle of the night when all of us are asleep"),
            ("natural_prose_stopwords", "In the morning I went to the store on a quiet street with all of my friends and you were there in the back of the room talking to a stranger about the way things are supposed to be when a day passes without any real news from the city or the coast."),
            ("meeting_note_prose", "Had a long meeting with the team today about the project schedule and all of the things we need to finish before the end of the month. We are not sure if the client will be ready for the next release, so we should check in with them tomorrow morning and see how they are doing."),
            ("diary_prose_unrelated", "I walked down to the bakery after breakfast to pick up some sourdough bread and a small jar of apricot jam. The weather was surprisingly warm for November and several neighbors were sitting outside on the porch reading newspapers and drinking tea while dogs chased leaves across the lawn."),
            ("tech_todo_note", "Remember to update the nginx configuration file on the staging server, restart the postgres database service, rotate the expired TLS certificate before Friday, and verify that all background worker queues drain cleanly after deployment."),
            ("short_stopword_note_10w", "I am going to the store for a bit"),
            ("prose_hitting_p060_partial", "Thinking about the architecture of a whole system when you are designing interfaces from scratch in the morning with a cup of coffee and no clear requirements from anyone on the team yet."),
            ("prose_hitting_p117_partial", "During the long review session we noticed that all the reports are partial and none of them explain why the shipment was delayed at the border last week."),
            ("prose_hitting_p121_partial", "People always say you are what you eat when they want to give unsolicited nutrition advice at dinner parties."),
            ("hitting_p060_exact_words_in_long_prose", "When taking high resolution screenshots on an external monitor you often forget that individual dots are merely pixels of a whole display surface and scaling changes everything you see on the glass panel."),
            ("hitting_p117_exact_words_in_long_prose", "When you read the news carefully you realize that all perspectives are partial and nobody has the complete picture of what happened during the negotiations last winter in Geneva or Vienna."),
            ("hitting_p068_short_ver_in_long_prose", "After sorting through three boxes of old tax paperwork on Tuesday afternoon I decided all day headlong i plunged into cleaning out the garage before dark."),
        ]
        for label, text in adversarial_probes:
            cands = mw.score_query(text, self.corpus)
            bucket = mw.classify_bucket(cands)
            self.assertEqual(bucket, "unmatched", f"{label} misclassified as {bucket}: {cands}")
            if cands:
                self.assertLess(cands[0]["score"], 0.40, f"{label} exceeded 0.40: {cands}")

    def test_ocr_corruptions_excerpts_and_self_retrieval_recall(self) -> None:
        # 1. Edge OCR corruptions on 4-token p060 still rank p060 #1 above unmatched threshold
        for noisy in ("Pixe1s 0f a wh01e", "pixelsof a whole", "Pix-\nels of awhole"):
            cands = mw.score_query(noisy, self.corpus)
            self.assertEqual(cands[0]["piece_id"], "p060", f"OCR variant {noisy!r}: {cands}")
            self.assertGreaterEqual(cands[0]["score"], 0.40, f"OCR variant {noisy!r}: {cands}")

        # 2. Intra-word [[ins: un]]finished on p003 & [[struck:...]] on p001
        cands_p003 = mw.score_query("Against the Frame of a home unfinished", self.corpus)
        self.assertEqual(cands_p003[0]["piece_id"], "p003")
        self.assertEqual(mw.classify_bucket(cands_p003), "high_confidence")

        cands_p001 = mw.score_query("Dying trees from seeds you've sown", self.corpus)
        self.assertEqual(cands_p001[0]["piece_id"], "p001")
        self.assertEqual(mw.classify_bucket(cands_p001), "high_confidence")

        # 3. Multi-page head/middle/tail excerpts on p020 and p099
        for pid in ("p020", "p099"):
            ver = [v for v in self.corpus.versions if v.piece_id == pid][0]
            toks = ver.clean_tokens
            mid_idx = len(toks) // 2
            for excerpt in (toks[:25], toks[mid_idx - 12 : mid_idx + 13], toks[-25:]):
                cands = mw.score_query(" ".join(excerpt), self.corpus)
                self.assertEqual(cands[0]["piece_id"], pid)
                self.assertEqual(mw.classify_bucket(cands), "high_confidence")

        # 4. All 156 versions self-retrieve #1 with high_confidence and unique piece_ids
        for ver in self.corpus.versions:
            cands = mw.score_query(" ".join(ver.clean_tokens), self.corpus)
            self.assertEqual(cands[0]["piece_id"], ver.piece_id, f"self-retrieval failed for {ver.version_id}")
            self.assertEqual(mw.classify_bucket(cands), "high_confidence", f"self-retrieval bucket for {ver.version_id}: {cands}")
            self.assertEqual(len({c["piece_id"] for c in cands}), len(cands))

    def test_shared_surface_full_pages_and_leaked_lines(self) -> None:
        jdata = json.loads(J_JSON.read_text(encoding="utf-8"))
        pages_by_id = {p["id"]: p for p in jdata["pages"]}

        def _page_text(page_id: str) -> str:
            lines: list[str] = []
            for blk in pages_by_id[page_id]["B"]:
                if blk.get("t") == 4:
                    continue
                for raw in blk.get("L", []):
                    c, _ = mw.clean_and_auth_text(raw)
                    if c:
                        lines.append(c)
            return " ".join(lines)

        # Full-page diary46 (7 pieces) and diary62a (p001 + p126) both remain ambiguous
        cands_46 = mw.score_query(_page_text("diary46"), self.corpus)
        self.assertEqual(mw.classify_bucket(cands_46), "ambiguous", f"diary46: {cands_46}")
        self.assertTrue({c["piece_id"] for c in cands_46} <= {f"p08{i}" for i in range(1, 8)})

        cands_62a = mw.score_query(_page_text("diary62a"), self.corpus)
        self.assertEqual(mw.classify_bucket(cands_62a), "ambiguous", f"diary62a: {cands_62a}")
        self.assertEqual({cands_62a[0]["piece_id"], cands_62a[1]["piece_id"]}, {"p001", "p126"})

        # Leaked line from p081 into p082 remains ambiguous
        leaked_82 = mw.score_query(
            "every day depression in a beautiful dress\n"
            "this is just a signal in my head\n"
            "watch the machinery crank in my head",
            self.corpus,
        )
        self.assertEqual(mw.classify_bucket(leaked_82), "ambiguous", f"leaked_82: {leaked_82}")
        self.assertEqual(leaked_82[0]["piece_id"], "p082")


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

    def test_default_review_report_refuses_when_intake_dir_inside_git_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / "git_repo"
            intake = repo_dir / "intake"
            intake.mkdir(parents=True)
            (repo_dir / ".git").mkdir()
            (intake / "photo_witnesses.json").write_text("[]", encoding="utf-8")
            out_path = Path(tmp) / "witness_links.json"

            rc, _, err = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)]
            )
            self.assertEqual(rc, 2)
            self.assertIn("git working tree", err)
            self.assertFalse((intake / "witness_review_report.md").exists())
            self.assertFalse(out_path.exists())

    def test_nonzero_ocr_cmd_exits_1_and_leaves_out_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            (intake / "photo_witnesses.json").write_text(
                json.dumps([{"photo_uuid": "FAIL-OCR-1", "witnessed_at": "2015-04-03T08:00:00Z"}]),
                encoding="utf-8",
            )
            out_path = Path(tmp) / "witness_links.json"
            sentinel = '{"schema":"versforms.witness-links.v1","photo_links":[],"note_links":[]}\n'
            out_path.write_text(sentinel, encoding="utf-8")

            rc, _, err = _run_cli(
                [
                    "--intake-dir",
                    str(intake),
                    "--out",
                    str(out_path),
                    "--j-json",
                    str(J_JSON),
                    "--run-ocr",
                    "--ocr-cmd",
                    f"{sys.executable} -c 'import sys; sys.exit(7)'",
                ]
            )
            self.assertEqual(rc, 1)
            self.assertIn("failed with exit 7", err)
            self.assertEqual(out_path.read_text(encoding="utf-8"), sentinel)

    def test_reviewed_entry_refreshes_candidates_when_sha256_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            out_path = Path(tmp) / "witness_links.json"
            (intake / "photo_witnesses.json").write_text(
                json.dumps(
                    [
                        {
                            "photo_uuid": "REV-PHOTO-1",
                            "witnessed_at": "2015-04-10T10:00:00Z",
                            "photo_sha256": "sha256:old_photo",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (intake / "ocr_cache.json").write_text(
                json.dumps({"REV-PHOTO-1": {"text": "pixels of a whole"}}),
                encoding="utf-8",
            )
            (intake / "ios_notes.json").write_text(
                json.dumps(
                    [
                        {
                            "note_id": "rev-note-1",
                            "created_at": "2015-04-10T11:00:00Z",
                            "modified_at": "2015-04-10T11:05:00Z",
                            "plaintext": "pixels of a whole",
                            "text_sha256": "sha256:old_note",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            rc, _, stderr = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)]
            )
            self.assertEqual(rc, 0, stderr)
            data = json.loads(out_path.read_text(encoding="utf-8"))
            data["photo_links"][0]["status"] = "confirmed"
            data["photo_links"][0]["confirmed_piece_id"] = "p060"
            data["photo_links"][0]["textual_state"] = "matches_scan"
            data["note_links"][0]["status"] = "confirmed"
            data["note_links"][0]["confirmed_piece_id"] = "p060"
            data["note_links"][0]["relation"] = "parallel_draft"
            out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

            # Change photo_sha256 & text_sha256 with updated OCR/note text pointing to p117
            (intake / "photo_witnesses.json").write_text(
                json.dumps(
                    [
                        {
                            "photo_uuid": "REV-PHOTO-1",
                            "witnessed_at": "2015-04-10T10:00:00Z",
                            "photo_sha256": "sha256:new_photo",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (intake / "ocr_cache.json").write_text(
                json.dumps({"REV-PHOTO-1": {"text": "all perspectives are partial"}}),
                encoding="utf-8",
            )
            (intake / "ios_notes.json").write_text(
                json.dumps(
                    [
                        {
                            "note_id": "rev-note-1",
                            "created_at": "2015-04-10T11:00:00Z",
                            "modified_at": "2015-04-10T12:00:00Z",
                            "plaintext": "all perspectives are partial",
                            "text_sha256": "sha256:new_note",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            rc, _, stderr = _run_cli(
                ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)]
            )
            self.assertEqual(rc, 0, stderr)
            refreshed = json.loads(out_path.read_text(encoding="utf-8"))
            p0 = refreshed["photo_links"][0]
            n0 = refreshed["note_links"][0]
            self.assertEqual(p0["status"], "confirmed")
            self.assertEqual(p0["confirmed_piece_id"], "p060")
            self.assertEqual(p0["textual_state"], "matches_scan")
            self.assertEqual(p0["photo_sha256"], "sha256:new_photo")
            self.assertEqual(p0["candidates"][0]["piece_id"], "p117")
            self.assertEqual(n0["status"], "confirmed")
            self.assertEqual(n0["confirmed_piece_id"], "p060")
            self.assertEqual(n0["relation"], "parallel_draft")
            self.assertEqual(n0["text_sha256"], "sha256:new_note")
            self.assertEqual(n0["candidates"][0]["piece_id"], "p117")

    def test_malformed_candidate_score_in_existing_out_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intake = Path(tmp) / "intake"
            intake.mkdir()
            (intake / "photo_witnesses.json").write_text("[]", encoding="utf-8")
            out_path = Path(tmp) / "witness_links.json"

            for bad_score in ('"bad_score"', "NaN", "true"):
                payload = (
                    '{"schema":"versforms.witness-links.v1","photo_links":[{"photo_uuid":"U1",'
                    '"status":"confirmed","candidates":[{"piece_id":"p060","score":'
                    + bad_score
                    + ',"token_overlap":1.0,"fuzzy_score":1.0}]}],"note_links":[]}'
                )
                out_path.write_text(payload, encoding="utf-8")
                rc, _, err = _run_cli(
                    ["--intake-dir", str(intake), "--out", str(out_path), "--j-json", str(J_JSON)]
                )
                self.assertEqual(rc, 2, f"Expected exit 2 for score={bad_score}: {err}")
                self.assertIn("failed to load inputs", err)
                self.assertEqual(out_path.read_text(encoding="utf-8"), payload)


if __name__ == "__main__":
    unittest.main()
