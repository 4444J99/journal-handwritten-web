"""Tier 3 pairwise pipelines (16), Tier 4 real-world scenarios (8), and Negative Controls (7)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from .cli_adapters import CliAdapter, JHWSandbox, get_target_config
from .fixtures import (
    CorpusIndex,
    build_metadata_laden_jpeg,
    build_poem_image,
    inject_digitized_at_into_chronology,
    inject_local_path_into_chronology,
    inject_osxphotos_into_jhw_tools,
    inject_p126_leak_into_projection,
    inject_pending_link_into_chronology,
    inject_plaintext_into_witness_links,
    make_ios_note,
    make_photo_witness,
    write_intake_bundle,
)
from .validators import (
    assert_cli_ok_or_handled_error,
    assert_git_clean,
    assert_jpeg_metadata_clean,
    assert_no_traceback,
    assert_mode_0600,
    assert_protected_paths_unchanged,
    assert_public_privacy_clean,
    assert_shared_surface_isolated,
    assert_two_clock_clean,
    assert_two_repo_boundary_clean,
    snapshot_protected_hashes,
    validate_chronology_schema,
    validate_ios_notes_schema,
    validate_ocr_cache_schema,
    validate_photo_witnesses_schema,
    validate_witness_links_schema,
)


def _write_stub_env(tmp_dir: Path, photos: list, notes: list, extra: dict[str, str] | None = None) -> dict[str, str]:
    p_path = tmp_dir / "stub_photos.json"
    n_path = tmp_dir / "stub_notes.json"
    p_path.write_text(json.dumps(photos, indent=2), encoding="utf-8")
    n_path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
    env = {"E2E_STUB_PHOTOS_JSON": str(p_path), "E2E_STUB_NOTES_JSON": str(n_path)}
    if extra:
        env.update(extra)
    return env


class Tier3PairwiseTests(unittest.TestCase):
    """16 cross-feature pairwise E2E pipelines (T3-P01 .. T3-P16)."""

    adapter: CliAdapter
    corpus: CorpusIndex

    @classmethod
    def setUpClass(cls) -> None:
        cfg = get_target_config()
        cls.adapter = CliAdapter(cfg)
        cls.corpus = CorpusIndex(cls.adapter.cfg.jhw_dir)

    def test_T3_P01_custody_and_photos_harvester(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p01_") as tmp:
            tmp_p = Path(tmp)
            photos = [
                {"photo_uuid": "P2", "original_filename": "2.JPG", "witnessed_at": "2015-03-01T10:00:00-05:00", "ismovie": False, "intrash": False, "albums": ["J"]},
                {"photo_uuid": "MOV", "original_filename": "M.MOV", "witnessed_at": "2015-02-01T10:00:00-05:00", "ismovie": True, "intrash": False, "albums": ["J"]},
                {"photo_uuid": "P1", "original_filename": "1.JPG", "witnessed_at": "2015-01-01T10:00:00-05:00", "ismovie": False, "intrash": False, "albums": ["J"]},
            ]
            env = _write_stub_env(tmp_p, photos=photos, notes=[])
            out = tmp_p / "ext_intake"
            res = self.adapter.tndc_witness(["--out-dir", str(out)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            pw = json.loads((out / "photo_witnesses.json").read_text(encoding="utf-8"))
            validate_photo_witnesses_schema(pw)
            self.assertEqual([x["photo_uuid"] for x in pw], ["P1", "P2"])
            assert_mode_0600(out / "photo_witnesses.json")

    def test_T3_P02_custody_and_notes_harvester(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p02_") as tmp:
            tmp_p = Path(tmp)
            notes = [
                {"note_id": "N1", "folder": "4_bloom", "title": "A", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": "p1", "password_protected": False},
                {"note_id": "NL", "folder": "4_bloom", "title": "L", "created_at": "2015-01-02T10:00:00-05:00", "modified_at": "2015-01-02T10:00:00-05:00", "plaintext": "locked", "password_protected": True},
                {"note_id": "N2", "folder": "4_bloom", "title": "B", "created_at": "2015-01-03T10:00:00-05:00", "modified_at": "2015-01-03T10:00:00-05:00", "plaintext": "p2", "password_protected": False},
            ]
            env = _write_stub_env(tmp_p, photos=[], notes=notes)
            out = tmp_p / "ext_intake"
            res = self.adapter.tndc_witness(["--out-dir", str(out)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            loaded = json.loads((out / "ios_notes.json").read_text(encoding="utf-8"))
            validate_ios_notes_schema(loaded)
            self.assertEqual([n["note_id"] for n in loaded], ["N1", "N2"])

    def test_T3_P03_photos_export_to_vision_ocr_cache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p03_") as tmp:
            tmp_p = Path(tmp)
            src = tmp_p / "src_p001.jpg"
            build_poem_image(src, ["The walls collapse"])
            photos = [
                {"photo_uuid": "U_P001", "original_filename": "p001.jpg", "witnessed_at": "2015-01-01T10:00:00-05:00", "source_path": str(src), "albums": ["J"]}
            ]
            env = _write_stub_env(
                tmp_p,
                photos=photos,
                notes=[],
                extra={"E2E_STUB_OCR_TEXT_MAP": json.dumps({"U_P001": "The walls collapse"})},
            )
            out = tmp_p / "ext_intake"
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--ocr"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            pw = json.loads((out / "photo_witnesses.json").read_text(encoding="utf-8"))
            cache = json.loads((out / "ocr_cache.json").read_text(encoding="utf-8"))
            validate_ocr_cache_schema(cache)
            self.assertEqual(set(cache.keys()), {pw[0]["photo_uuid"]})

    def test_T3_P04_stage1_photos_ocr_to_stage2_matcher(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p04_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p3 = intake / "photos" / "U3.jpg"
            p67 = intake / "photos" / "U67.jpg"
            build_poem_image(p3, ["A Flower is a Flower"])
            build_poem_image(p67, ["p067"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U3", "3.jpg", p3, "2015-02-01T10:00:00-05:00"),
                    make_photo_witness("U67", "67.jpg", p67, "2015-03-01T10:00:00-05:00"),
                ],
                notes=[],
                ocr_cache={
                    "U3": {"text": self.corpus.extract_version_text("p003"), "lines": ["A Flower"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U67": {"text": self.corpus.extract_version_text("p067"), "lines": ["p067"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            res = self.adapter.jhw_match(sb, intake)
            self.assertEqual(res.returncode, 0, res.stderr)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            self.assertEqual(links["photo_links"][0]["candidates"][0]["piece_id"], "p003")
            self.assertEqual(links["photo_links"][1]["candidates"][0]["piece_id"], "p067")
            self.assertTrue(all(p["status"] == "pending_review" for p in links["photo_links"]))

    def test_T3_P05_stage1_notes_to_stage2_matcher(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p05_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[
                    make_ios_note("N81", "4_bloom", "T81", "2015-04-01T10:00:00-04:00", "2015-04-01T10:00:00-04:00", self.corpus.extract_version_text("p081")),
                    make_ios_note("N126", "4_bloom", "T126", "2015-05-01T10:00:00-04:00", "2015-05-01T10:00:00-04:00", self.corpus.extract_version_text("p126")),
                ],
                ocr_cache={},
            )
            res = self.adapter.jhw_match(sb, intake)
            self.assertEqual(res.returncode, 0, res.stderr)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            self.assertEqual(links["note_links"][0]["candidates"][0]["piece_id"], "p081")
            self.assertEqual(links["note_links"][1]["candidates"][0]["piece_id"], "p126")
            self.assertTrue(all(n["status"] == "pending_review" and n["relation"] == "unreviewed" for n in links["note_links"]))

    def test_T3_P06_on_demand_ocr_hook_populates_external_cache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p06_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["The walls collapse"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00")],
                notes=[],
            )
            self.assertFalse((intake / "ocr_cache.json").exists())
            if self.adapter.cfg.self_check:
                hook = f"{sys.executable} -m tests.e2e_witness.stubs tndc-witness --out-dir {{intake_dir}} --ocr-only"
                res = self.adapter.jhw_match(sb, intake, extra_args=["--ocr-cmd", hook])
            else:
                res = self.adapter.jhw_match(sb, intake)
            assert_no_traceback(res, "T3_P06 match")
            if assert_cli_ok_or_handled_error(res, "T3_P06 match"):
                if self.adapter.cfg.self_check:
                    self.assertTrue((intake / "ocr_cache.json").is_file(), res.stdout + res.stderr)
                    validate_ocr_cache_schema(
                        json.loads((intake / "ocr_cache.json").read_text(encoding="utf-8"))
                    )
                out = sb / "source" / "witness_links.json"
                self.assertTrue(out.is_file(), f"witness_links.json missing: {res.stderr}")
                validate_witness_links_schema(
                    json.loads(out.read_text(encoding="utf-8"))
                )

    def test_T3_P07_matcher_and_public_privacy_hygiene(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p07_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["The walls"])
            pw = make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00")
            pw["local_path"] = "/Users/example/Private/U1.jpg"
            write_intake_bundle(
                intake,
                photos=[pw],
                notes=[make_ios_note("N1", "PrivateFolder", "PrivateTitle", "2015-01-02T10:00:00-05:00", "2015-01-02T10:00:00-05:00", "SECRET_BODY_P07")],
                ocr_cache={"U1": {"text": "RAW_OCR_P07", "lines": ["RAW_OCR_P07"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            assert_public_privacy_clean(links, forbidden_substrings=("SECRET_BODY_P07", "RAW_OCR_P07", "PrivateFolder", "PrivateTitle"))

    def test_T3_P08_pending_gate_excludes_unconfirmed_from_chronology(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p08_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["The walls"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00")],
                notes=[make_ios_note("N1", "F", "T", "2015-01-02T10:00:00-05:00", "2015-01-02T10:00:00-05:00", "A Flower is a Flower")],
                ocr_cache={"U1": {"text": "The walls", "lines": ["The walls"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            for e in chron["physical_codex_order"]:
                self.assertEqual(e["witnesses"]["photo_witnesses"], [])
                self.assertEqual(e["witnesses"]["linked_ios_notes"], [])

    def test_T3_P09_confirmed_flow_anchors_interpolates_and_interleaves_note(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p09_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p3 = intake / "photos" / "U3.jpg"
            p67 = intake / "photos" / "U67.jpg"
            build_poem_image(p3, ["A Flower"])
            build_poem_image(p67, ["p067"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U3", "3.jpg", p3, "2015-02-01T10:00:00-05:00"),
                    make_photo_witness("U67", "67.jpg", p67, "2015-04-01T10:00:00-04:00"),
                ],
                notes=[make_ios_note("N39", "F", "T", "2015-03-01T10:00:00-05:00", "2015-03-01T10:00:00-05:00", self.corpus.extract_version_text("p039"))],
                ocr_cache={
                    "U3": {"text": self.corpus.extract_version_text("p003"), "lines": ["f"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U67": {"text": self.corpus.extract_version_text("p067"), "lines": ["p"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p003"
            links["photo_links"][1]["status"] = "confirmed"
            links["photo_links"][1]["confirmed_piece_id"] = "p067"
            links["note_links"][0]["status"] = "confirmed"
            links["note_links"][0]["confirmed_piece_id"] = "p039"
            links["note_links"][0]["relation"] = "parallel_draft"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            validate_chronology_schema(chron, self.corpus, links)
            by_pid = {e["piece_id"]: e for e in chron["physical_codex_order"]}
            self.assertEqual(by_pid["p003"]["chronology"]["date_basis"], "photo_anchored")
            self.assertEqual(by_pid["p067"]["chronology"]["date_basis"], "photo_anchored")
            self.assertEqual(by_pid["p001"]["chronology"]["date_basis"], "extrapolated_head")
            self.assertEqual(by_pid["p039"]["chronology"]["date_basis"], "interpolated")
            self.assertEqual(len(by_pid["p039"]["witnesses"]["linked_ios_notes"]), 1)

    def test_T3_P10_idempotent_rerun_with_new_arrival(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p10_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["The walls"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00")],
                notes=[],
                ocr_cache={"U1": {"text": self.corpus.extract_version_text("p001"), "lines": ["w"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p001"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            p125 = intake / "photos" / "U125.jpg"
            build_poem_image(p125, ["p125"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00"),
                    make_photo_witness("U125", "125.jpg", p125, "2015-06-01T10:00:00-04:00"),
                ],
                notes=[],
                ocr_cache={
                    "U1": {"text": self.corpus.extract_version_text("p001"), "lines": ["w"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U125": {"text": self.corpus.extract_version_text("p125"), "lines": ["125"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            self.adapter.jhw_match(sb, intake)
            rerun = json.loads(lp.read_text(encoding="utf-8"))
            self.assertEqual(rerun["photo_links"][0]["status"], "confirmed")
            self.assertEqual(rerun["photo_links"][1]["status"], "pending_review")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            validate_chronology_schema(chron, self.corpus, rerun)

    def test_T3_P11_chronology_privacy_audit_clean(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p11_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["The walls"])
            pw = make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00")
            pw["local_path"] = "/Users/example/Private/SECRET_PATH_P11.jpg"
            write_intake_bundle(
                intake,
                photos=[pw],
                notes=[make_ios_note("N1", "PrivFld", "PrivTit", "2015-01-02T10:00:00-05:00", "2015-01-02T10:00:00-05:00", "PRIV_NOTE_P11")],
                ocr_cache={"U1": {"text": "PRIV_OCR_P11", "lines": ["p"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p001"
            links["note_links"][0]["status"] = "confirmed"
            links["note_links"][0]["relation"] = "standalone_cohort"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            assert_public_privacy_clean(
                json.loads(cp.read_text(encoding="utf-8")),
                forbidden_substrings=("SECRET_PATH_P11", "PRIV_NOTE_P11", "PRIV_OCR_P11", "PrivFld", "PrivTit"),
            )

    def test_T3_P12_chronology_to_round1_diary62a_isolation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p12_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(json.dumps({"schema": "versforms.witness-links.v1", "generated_at": "2026-11-24T00:00:00Z", "intake_summary": {}, "photo_links": [], "note_links": []}))
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            out1 = Path(tmp) / "out1"
            out2 = Path(tmp) / "out2"
            self.adapter.jhw_export_round1(sb, cp, out1, pieces=["p001"], extra_args=["--surface", "diary62a"])
            self.adapter.jhw_export_round1(sb, cp, out2, pieces=["p126"], extra_args=["--surface", "diary62a"])
            m1 = json.loads((out1 / "projection_manifest.json").read_text(encoding="utf-8"))
            m2 = json.loads((out2 / "projection_manifest.json").read_text(encoding="utf-8"))
            assert_shared_surface_isolated(m1, out1, self.corpus)
            assert_shared_surface_isolated(m2, out2, self.corpus)

    def test_T3_P13_full_jhw_pipeline_keeps_check_and_boundary_clean(self) -> None:
        before = snapshot_protected_hashes(self.adapter.cfg.jhw_dir)
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p13_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            self.adapter.jhw_match(sb, intake)
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", cp)
            self.adapter.jhw_export_round1(sb, cp, Path(tmp) / "proj", pieces=["p001"])
        assert_two_repo_boundary_clean(self.adapter.cfg.jhw_dir)
        res = self.adapter.jhw_check()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        assert_protected_paths_unchanged(self.adapter.cfg.jhw_dir, before)

    def test_T3_P14_stage0_dryrun_then_live_harvester(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t3_p14_") as tmp:
            tmp_p = Path(tmp)
            env = _write_stub_env(
                tmp_p,
                photos=[{"photo_uuid": "U1", "original_filename": "1.JPG", "witnessed_at": "2015-01-01T10:00:00-05:00", "albums": ["J"]}],
                notes=[{"note_id": "N1", "folder": "4_bloom", "title": "T", "created_at": "2015-01-02T10:00:00-05:00", "modified_at": "2015-01-02T10:00:00-05:00", "plaintext": "body"}],
            )
            r0 = self.adapter.tndc_preflight(["--json"], extra_env=env)
            self.assertEqual(r0.returncode, 0, r0.stderr)
            out = tmp_p / "ext"
            r_dry = self.adapter.tndc_witness(["--out-dir", str(out), "--dry-run"], extra_env=env)
            self.assertEqual(r_dry.returncode, 0, r_dry.stderr)
            self.assertFalse(out.exists())
            r_live = self.adapter.tndc_witness(["--out-dir", str(out)], extra_env=env)
            self.assertEqual(r_live.returncode, 0, r_live.stderr)
            validate_photo_witnesses_schema(json.loads((out / "photo_witnesses.json").read_text(encoding="utf-8")))
            validate_ios_notes_schema(json.loads((out / "ios_notes.json").read_text(encoding="utf-8")))

    def test_T3_P15_both_repo_test_suites_and_linters_pass(self) -> None:
        r_tndc = self.adapter.tndc_run_tests()
        r_ruff = self.adapter.tndc_run_ruff()
        r_jhw = self.adapter.jhw_check()
        self.assertEqual(r_tndc.returncode, 0, r_tndc.stderr)
        self.assertEqual(r_ruff.returncode, 0, r_ruff.stderr)
        self.assertEqual(r_jhw.returncode, 0, r_jhw.stderr)

    def test_T3_P16_runner_orchestrates_env_and_tiers(self) -> None:
        runner = Path(__file__).resolve().parent / "run_e2e.py"
        res = subprocess.run(
            [sys.executable, str(runner), "--self-check", "--tier", "3", "--filter", "T3_P01", "--json"],
            cwd=str(self.adapter.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data["failed"], 0)
        self.assertEqual(data["passed"], 1)


class Tier4ScenarioTests(unittest.TestCase):
    """8 realistic end-to-end application scenarios (T4-S01 .. T4-S08)."""

    adapter: CliAdapter
    corpus: CorpusIndex

    @classmethod
    def setUpClass(cls) -> None:
        cfg = get_target_config()
        cls.adapter = CliAdapter(cfg)
        cls.corpus = CorpusIndex(cls.adapter.cfg.jhw_dir)

    def test_T4_S01_multi_poem_cohort_diary46_7_pieces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t4_s01_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p46 = intake / "photos" / "U46.jpg"
            p42 = intake / "photos" / "U42.jpg"
            build_metadata_laden_jpeg(p46, lines=["every day depression in a beautiful dress"])
            build_poem_image(p42, ["p073"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U42", "42.jpg", p42, "2015-04-20T12:00:00-04:00"),
                    make_photo_witness("U46", "46.jpg", p46, "2015-05-02T18:10:00-04:00"),
                ],
                notes=[],
                ocr_cache={
                    "U42": {"text": self.corpus.extract_version_text("p073"), "lines": ["p073"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U46": {"text": "every day depression in a beautiful dress\nthis is just a signal in my head", "lines": ["every day depression"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p073"
            links["photo_links"][1]["status"] = "confirmed"
            links["photo_links"][1]["confirmed_piece_id"] = "p081"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            by_pid = {e["piece_id"]: e for e in chron["physical_codex_order"]}
            for pid in ("p081", "p082", "p083", "p084", "p085", "p086", "p087"):
                self.assertTrue(by_pid[pid]["witnesses"]["codex_scan"]["shared_surface"])
                self.assertEqual(by_pid[pid]["chronology"]["date_basis"], "photo_anchored")

            out_dir = Path(tmp) / "proj"
            res = self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p081"])
            self.assertEqual(res.returncode, 0, res.stderr)
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            assert_shared_surface_isolated(manifest, out_dir, self.corpus)

    def test_T4_S02_multi_version_p001_diary1_and_diary62a_accepted_readings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t4_s02_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            p62 = intake / "photos" / "U62.jpg"
            build_poem_image(p1, ["The walls collapse"])
            build_poem_image(p62, ["MINOTAUR, where are you now?"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U1", "1.jpg", p1, "2014-10-05T10:00:00-04:00"),
                    make_photo_witness("U62", "62.jpg", p62, "2015-07-18T10:00:00-04:00"),
                ],
                notes=[],
                ocr_cache={
                    "U1": {"text": self.corpus.extract_version_text("p001", "p001-diary1-0"), "lines": ["w"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U62": {"text": "MINOTAUR, where are you now? (OF which) you were so fond (OF) The walls were so simple", "lines": ["m"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            self.assertEqual(links["photo_links"][0]["candidates"][0]["piece_id"], "p001")
            self.assertEqual(links["photo_links"][1]["candidates"][0]["piece_id"], "p001")
            for pl in links["photo_links"]:
                pl["status"] = "confirmed"
                pl["confirmed_piece_id"] = "p001"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            p001 = next(e for e in chron["physical_codex_order"] if e["piece_id"] == "p001")
            self.assertEqual(len(p001["witnesses"]["photo_witnesses"]), 2)

            out_dir = Path(tmp) / "proj"
            self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p001"], extra_args=["--surface", "diary62a"])
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            assert_shared_surface_isolated(manifest, out_dir, self.corpus)

    def test_T4_S03_multi_page_spanning_versions_p020_and_p052(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t4_s03_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p20 = intake / "photos" / "U20.jpg"
            p52 = intake / "photos" / "U52.jpg"
            build_poem_image(p20, ["p020"])
            build_poem_image(p52, ["p052"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U20", "20.jpg", p20, "2015-01-19T10:00:00-05:00"),
                    make_photo_witness("U52", "52.jpg", p52, "2015-03-04T10:00:00-05:00"),
                ],
                notes=[],
                ocr_cache={
                    "U20": {"text": self.corpus.extract_version_text("p020", "p020-diary13a-0")[:300], "lines": ["p20"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U52": {"text": self.corpus.extract_version_text("p052", "p052-diary31a-1"), "lines": ["p52"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p020"
            links["photo_links"][1]["status"] = "confirmed"
            links["photo_links"][1]["confirmed_piece_id"] = "p052"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            validate_chronology_schema(chron, self.corpus, links)
            by_pid = {e["piece_id"]: e for e in chron["physical_codex_order"]}
            self.assertTrue(by_pid["p053"]["witnesses"]["codex_scan"]["shared_surface"])
            self.assertEqual(by_pid["p030"]["chronology"]["date_basis"], "interpolated")

    def test_T4_S04_interleaved_apple_notes_and_locked_note_skip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t4_s04_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            tmp_p = Path(tmp)
            raw_notes = [
                {"note_id": "NA", "folder": "4_bloom", "title": "PrivA", "created_at": "2015-02-10T10:00:00-05:00", "modified_at": "2015-02-10T10:00:00-05:00", "plaintext": "Standalone cohort private text", "password_protected": False},
                {"note_id": "NB", "folder": "4_bloom", "title": "PrivB", "created_at": "2015-03-01T10:00:00-05:00", "modified_at": "2015-03-01T10:00:00-05:00", "plaintext": self.corpus.extract_version_text("p039"), "password_protected": False},
                {"note_id": "NC", "folder": "4_bloom", "title": "PrivC", "created_at": "2015-04-05T10:00:00-04:00", "modified_at": "2015-04-05T10:00:00-04:00", "plaintext": self.corpus.extract_version_text("p067"), "password_protected": False},
                {"note_id": "NLOCK", "folder": "4_bloom", "title": "Locked", "created_at": "2015-04-10T10:00:00-04:00", "modified_at": "2015-04-10T10:00:00-04:00", "plaintext": "NEVER_CAPTURE", "password_protected": True},
            ]
            env = _write_stub_env(tmp_p, photos=[], notes=raw_notes)
            intake = tmp_p / "intake"
            self.adapter.tndc_witness(["--out-dir", str(intake)], extra_env=env)
            ios_notes = json.loads((intake / "ios_notes.json").read_text(encoding="utf-8"))
            self.assertEqual([n["note_id"] for n in ios_notes], ["NA", "NB", "NC"])

            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["note_links"][0]["status"] = "confirmed"
            links["note_links"][0]["relation"] = "standalone_cohort"
            links["note_links"][1]["status"] = "confirmed"
            links["note_links"][1]["confirmed_piece_id"] = "p039"
            links["note_links"][1]["relation"] = "source_fragment"
            links["note_links"][2]["status"] = "confirmed"
            links["note_links"][2]["confirmed_piece_id"] = "p067"
            links["note_links"][2]["relation"] = "parallel_draft"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            validate_chronology_schema(chron, self.corpus, links)
            assert_public_privacy_clean(links, forbidden_substrings=("Standalone cohort private text", "PrivA", "4_bloom"))
            assert_public_privacy_clean(chron, forbidden_substrings=("Standalone cohort private text", "PrivA", "4_bloom"))
            note_order = [e["note_id"] for e in chron["amalgamated_chronological_order"] if e.get("entry_type") == "ios_note"]
            self.assertEqual(note_order, ["NA", "NB", "NC"])

    def test_T4_S05_prescan_edited_photo_and_two_clock_tail_extrapolation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t4_s05_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p7 = intake / "photos" / "U7.jpg"
            p88 = intake / "photos" / "U88.jpg"
            build_poem_image(p7, ["p007"])
            build_poem_image(p88, ["p088"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U7", "7.jpg", p7, "2014-11-12T09:00:00-05:00"),
                    make_photo_witness("U88", "88.jpg", p88, "2015-06-01T09:00:00-04:00"),
                ],
                notes=[],
                ocr_cache={
                    "U7": {"text": self.corpus.extract_version_text("p007"), "lines": ["p007"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U88": {"text": self.corpus.extract_version_text("p088"), "lines": ["p088"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p007"
            links["photo_links"][0]["textual_state"] = "predates_scan_edits"
            links["photo_links"][1]["status"] = "confirmed"
            links["photo_links"][1]["confirmed_piece_id"] = "p088"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp_a = Path(tmp) / "ca.json"
            cp_b = Path(tmp) / "cb.json"
            self.adapter.jhw_chronology(sb, lp, cp_a, digitized_at="2015-09")
            self.adapter.jhw_chronology(sb, lp, cp_b, digitized_at="2022-01")
            ca = json.loads(cp_a.read_text(encoding="utf-8"))
            cb = json.loads(cp_b.read_text(encoding="utf-8"))
            p007 = next(e for e in ca["physical_codex_order"] if e["piece_id"] == "p007")
            self.assertEqual(p007["witnesses"]["photo_witnesses"][0]["textual_state"], "predates_scan_edits")
            p126 = next(e for e in ca["physical_codex_order"] if e["piece_id"] == "p126")
            self.assertEqual(p126["chronology"]["date_basis"], "extrapolated_tail")
            self.assertEqual(ca["physical_codex_order"][-1]["chronology"], cb["physical_codex_order"][-1]["chronology"])

    def test_T4_S06_round1_batch_export_isolation_and_metadata_wipe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t4_s06_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(json.dumps({"schema": "versforms.witness-links.v1", "generated_at": "2026-11-24T00:00:00Z", "intake_summary": {}, "photo_links": [], "note_links": []}))
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            out_dir = Path(tmp) / "proj"
            self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p001", "p126", "p067", "p113"])
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            assert_shared_surface_isolated(manifest, out_dir, self.corpus)
            exported_pids = {e["piece_id"] for e in manifest["exports"]}
            blocked_pids = {b["piece_id"] for b in manifest["blocked"]}
            self.assertIn("p001", exported_pids)
            self.assertIn("p126", exported_pids)
            self.assertEqual(blocked_pids, {"p067", "p113"})

            out_25 = Path(tmp) / "proj25"
            self.adapter.jhw_export_round1(sb, cp, out_25, pieces=["p039"], extra_args=["--surface", "diary25"])
            m25 = json.loads((out_25 / "projection_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(m25["exports"], [])
            self.assertEqual(len(m25["blocked"]), 1)

    def test_T4_S07_rerun_idempotency_partial_confirmation_and_new_arrivals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t4_s07_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            tmp_p = Path(tmp)
            intake = tmp_p / "intake"
            photos_r1 = [
                {"photo_uuid": "U3", "original_filename": "3.JPG", "witnessed_at": "2015-01-10T10:00:00-05:00", "albums": ["J"]},
                {"photo_uuid": "U6", "original_filename": "6.JPG", "witnessed_at": "2015-01-20T10:00:00-05:00", "albums": ["J"]},
            ]
            notes_r1 = [
                {"note_id": "N1", "folder": "4_bloom", "title": "1", "created_at": "2015-01-11T10:00:00-05:00", "modified_at": "2015-01-11T10:00:00-05:00", "plaintext": "unrelated gibberish"},
                {"note_id": "N2", "folder": "4_bloom", "title": "2", "created_at": "2015-01-21T10:00:00-05:00", "modified_at": "2015-01-21T10:00:00-05:00", "plaintext": self.corpus.extract_version_text("p009")},
            ]
            ocr_r1 = {
                "U3": self.corpus.extract_version_text("p003"),
                "U6": self.corpus.extract_version_text("p006"),
            }
            env1 = _write_stub_env(tmp_p, photos_r1, notes_r1, {"E2E_STUB_OCR_TEXT_MAP": json.dumps(ocr_r1)})
            self.adapter.tndc_witness(["--out-dir", str(intake), "--ocr"], extra_env=env1)
            (intake / "photos" / "U3_3.JPG").write_bytes(b"SENTINEL_KEEP")

            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p003"
            links["note_links"][0]["status"] = "rejected"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            photos_r2 = photos_r1 + [{"photo_uuid": "U99", "original_filename": "99.JPG", "witnessed_at": "2015-05-01T10:00:00-04:00", "albums": ["J"]}]
            notes_r2 = notes_r1 + [{"note_id": "N3", "folder": "4_bloom", "title": "3", "created_at": "2015-05-02T10:00:00-04:00", "modified_at": "2015-05-02T10:00:00-04:00", "plaintext": self.corpus.extract_version_text("p099")[:200]}]
            ocr_r2 = dict(ocr_r1, U99=self.corpus.extract_version_text("p099")[:200])
            env2 = _write_stub_env(tmp_p, photos_r2, notes_r2, {"E2E_STUB_OCR_TEXT_MAP": json.dumps(ocr_r2)})
            self.adapter.tndc_witness(["--out-dir", str(intake), "--ocr"], extra_env=env2)
            self.assertEqual((intake / "photos" / "U3_3.JPG").read_bytes(), b"SENTINEL_KEEP")

            self.adapter.jhw_match(sb, intake)
            rerun = json.loads(lp.read_text(encoding="utf-8"))
            self.assertEqual(rerun["photo_links"][0]["status"], "confirmed")
            self.assertEqual(rerun["photo_links"][1]["status"], "pending_review")
            self.assertEqual(rerun["photo_links"][2]["status"], "pending_review")
            self.assertEqual(rerun["note_links"][0]["status"], "rejected")
            self.assertEqual(rerun["note_links"][1]["status"], "pending_review")
            self.assertEqual(rerun["note_links"][2]["status"], "pending_review")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            validate_chronology_schema(chron, self.corpus, rerun)

    def test_T4_S08_full_two_repo_custody_and_integrity_audit(self) -> None:
        before = snapshot_protected_hashes(self.adapter.cfg.jhw_dir)
        assert_two_repo_boundary_clean(self.adapter.cfg.jhw_dir)
        self.assertEqual(self.adapter.jhw_check().returncode, 0)
        ci = self.adapter.jhw_ci_local(only=("check",))
        self.assertEqual(ci.returncode, 0, ci.stdout + ci.stderr)
        ut = subprocess.run(
            [str(self.adapter.jhw_python()), "-m", "unittest", "tests/test_check_manifest.py", "tests/test_silent_launch_lint.py"],
            cwd=str(self.adapter.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(ut.returncode, 0, ut.stdout + ut.stderr)
        self.assertEqual(self.adapter.tndc_run_tests().returncode, 0)
        self.assertEqual(self.adapter.tndc_run_ruff().returncode, 0)
        assert_protected_paths_unchanged(self.adapter.cfg.jhw_dir, before)
        if os.environ.get("E2E_REQUIRE_CLEAN_GIT") == "1":
            assert_git_clean(self.adapter.cfg.jhw_dir, "jhw")


class NegativeControlTests(unittest.TestCase):
    """7 fault-injection checks proving validators fail loudly on every violated invariant."""

    adapter: CliAdapter
    corpus: CorpusIndex

    @classmethod
    def setUpClass(cls) -> None:
        cfg = get_target_config()
        cls.adapter = CliAdapter(cfg)
        cls.corpus = CorpusIndex(cls.adapter.cfg.jhw_dir)

    def test_NC_01_plaintext_in_witness_links_rejected(self) -> None:
        bad = inject_plaintext_into_witness_links({"photo_links": [], "note_links": []})
        with self.assertRaises(AssertionError):
            assert_public_privacy_clean(bad)

    def test_NC_02_local_path_in_chronology_rejected(self) -> None:
        bad = inject_local_path_into_chronology({"physical_codex_order": [{"piece_id": "p001"}]})
        with self.assertRaises(AssertionError):
            assert_public_privacy_clean(bad)

    def test_NC_03_digitized_at_used_as_est_end_rejected(self) -> None:
        chron = {
            "physical_codex_order": [
                {
                    "piece_id": "p126",
                    "witnesses": {"codex_scan": {"digitized_at": "2015-09"}},
                    "chronology": {"est_start": "2015-08-01", "est_end": "2015-08-10", "amalgamated_sort_key": "2015-08-10#p126"},
                }
            ]
        }
        bad = inject_digitized_at_into_chronology(chron, "2015-09")
        with self.assertRaises(AssertionError):
            assert_two_clock_clean(bad, "2015-09")

    def test_NC_04_unstripped_metadata_laden_jpeg_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_nc04_") as tmp:
            dirty = Path(tmp) / "dirty.jpg"
            build_metadata_laden_jpeg(dirty, lines=["NC04"])
            with self.assertRaises(AssertionError):
                assert_jpeg_metadata_clean(dirty)

    def test_NC_05_p126_leak_into_p001_diary62a_projection_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_nc05_") as tmp:
            out_dir = Path(tmp)
            # (a) near-full-page crop on the 7-piece diary46 page (M5b).
            page46 = self.corpus.page_by_id["diary46"]
            near_full_size = (page46["iw"] - 1, page46["ih"] - 1)
            near_full = out_dir / "diary46_near_full.jpg"
            Image.new("RGB", near_full_size, (255, 255, 255)).save(near_full, format="JPEG")
            bad_near_full = {
                "exports": [
                    {
                        "piece_id": "p081",
                        "surface_id": "diary46",
                        "output_file": near_full.name,
                        "isolated_crop": True,
                        "crop_box": [0, 0, *near_full_size],
                        "dimensions": list(near_full_size),
                    }
                ]
            }
            with self.assertRaises(AssertionError):
                assert_shared_surface_isolated(bad_near_full, out_dir, self.corpus)

            # (b) uncropped diary62a JPEG on disk with a spoofed small crop_box (M5b3).
            page62 = self.corpus.page_by_id["diary62a"]
            full_size = (page62["iw"], page62["ih"])
            uncropped = out_dir / "diary62a_uncropped.jpg"
            Image.new("RGB", full_size, (255, 255, 255)).save(uncropped, format="JPEG")
            spoof_box = list(self.corpus.piece_block_bbox("p001", "diary62a") or (0, 0, 10, 10))
            bad_spoof = {
                "exports": [
                    {
                        "piece_id": "p001",
                        "surface_id": "diary62a",
                        "output_file": uncropped.name,
                        "isolated_crop": True,
                        "crop_box": spoof_box,
                        "dimensions": [spoof_box[2] - spoof_box[0], spoof_box[3] - spoof_box[1]],
                    }
                ]
            }
            with self.assertRaises(AssertionError):
                assert_shared_surface_isolated(bad_spoof, out_dir, self.corpus)

            # (c) original p126 neighbor-block exposure claim (existing control).
            bad_manifest = inject_p126_leak_into_projection({"exports": []}, self.corpus)
            with self.assertRaises(AssertionError):
                assert_shared_surface_isolated(bad_manifest, out_dir, self.corpus)

    def test_NC_06_pending_review_promoted_into_chronology_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_nc06_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(json.dumps({"schema": "versforms.witness-links.v1", "generated_at": "2026-11-24T00:00:00Z", "intake_summary": {}, "photo_links": [], "note_links": []}))
            cp = Path(tmp) / "chron.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            bad = inject_pending_link_into_chronology(chron)
            with self.assertRaises(AssertionError):
                validate_chronology_schema(bad, self.corpus)

    def test_NC_07_osxphotos_in_jhw_tools_rejected(self) -> None:
        with JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            inject_osxphotos_into_jhw_tools(sb)
            with self.assertRaises(AssertionError):
                assert_two_repo_boundary_clean(sb)
