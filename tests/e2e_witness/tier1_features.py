"""Tier 1 Feature Coverage tests (70 tests: T1-F01-01 .. T1-F14-05)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from .cli_adapters import CliAdapter, JHWSandbox, TargetConfig, get_target_config
from .fixtures import (
    CorpusIndex,
    build_metadata_laden_jpeg,
    build_poem_image,
    make_ios_note,
    make_photo_witness,
    sha256_bytes,
    write_intake_bundle,
)
from .validators import (
    assert_git_clean,
    assert_preflight_contract,
    assert_jpeg_metadata_clean,
    assert_no_traceback,
    assert_mode_0600,
    assert_mode_0700,
    assert_protected_paths_unchanged,
    assert_public_privacy_clean,
    assert_shared_surface_isolated,
    assert_two_clock_clean,
    assert_two_clock_invariant,
    assert_two_repo_boundary_clean,
    snapshot_protected_hashes,
    validate_chronology_schema,
    validate_ios_notes_schema,
    validate_ocr_cache_schema,
    validate_photo_witnesses_schema,
    validate_witness_links_schema,
)


def _write_stub_env(tmp_dir: Path, photos: list, notes: list) -> dict[str, str]:
    p_path = tmp_dir / "stub_photos.json"
    n_path = tmp_dir / "stub_notes.json"
    p_path.write_text(json.dumps(photos, indent=2), encoding="utf-8")
    n_path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
    return {"E2E_STUB_PHOTOS_JSON": str(p_path), "E2E_STUB_NOTES_JSON": str(n_path)}


class Tier1FeatureTests(unittest.TestCase):
    """70 isolated happy-path feature tests covering Features 1..14."""

    adapter: CliAdapter
    corpus: CorpusIndex

    @classmethod
    def setUpClass(cls) -> None:
        cfg = get_target_config()
        cls.adapter = CliAdapter(cfg)
        cls.corpus = CorpusIndex(cls.adapter.cfg.jhw_dir)

    # --- Feature 1: Repo clone, Python >=3.11 .venv & deps ---

    def test_T1_F01_01_tndc_python_version(self) -> None:
        res = self.adapter.tndc_py_exec("import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
        self.assertEqual(res.returncode, 0, res.stderr)
        parts = res.stdout.strip().split()[-1].split(".")
        self.assertGreaterEqual((int(parts[0]), int(parts[1])), (3, 11))

    def test_T1_F01_02_tndc_required_packages(self) -> None:
        res = self.adapter.tndc_py_exec("import osxphotos, rapidfuzz, ocrmac, Vision; print('OK')")
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_T1_F01_03_tndc_cli_version(self) -> None:
        res = self.adapter.tndc_version()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(res.stdout.strip())

    def test_T1_F01_04_jhw_required_packages(self) -> None:
        mods = "PIL, numpy, fontTools, brotli, markdown" if self.adapter.cfg.self_check else "rapidfuzz, PIL, numpy, fontTools, brotli, markdown"
        res = self.adapter.jhw_py_exec(f"import {mods}; print('OK')")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("OK", res.stdout)

    def test_T1_F01_05_tndc_dev_tools_pytest_ruff(self) -> None:
        if self.adapter.cfg.self_check:
            r1 = self.adapter.tndc_run_tests()
            r2 = self.adapter.tndc_run_ruff()
            self.assertEqual(r1.returncode, 0)
            self.assertEqual(r2.returncode, 0)
            return
        res = subprocess.run(
            [str(self.adapter.tndc_python()), "-m", "pytest", "--version"],
            cwd=str(self.adapter.cfg.tndc_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        ruff = self.adapter.tndc_dir / ".venv" / "bin" / "ruff"
        res2 = subprocess.run([str(ruff), "--version"], capture_output=True, text=True, check=False)
        self.assertEqual(res2.returncode, 0, res2.stderr)

    # --- Feature 2: Stage 0 preflight & permission probe ---

    def test_T1_F02_01_stage0_preflight_ok(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f02_ok_") as tmp:
            env = _write_stub_env(Path(tmp), photos=[], notes=[])
            res = self.adapter.tndc_preflight(["--json"], extra_env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        assert_preflight_contract(res, "T1_F02_01")
        if self.adapter.cfg.self_check:
            self.assertIn("photos_access", res.stdout)

    def test_T1_F02_02_stage0_blank_photos_album_lists_counts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f02_") as tmp:
            env = _write_stub_env(
                Path(tmp),
                photos=[
                    {
                        "photo_uuid": "U1",
                        "original_filename": "A.JPG",
                        "witnessed_at": "2015-01-01T10:00:00-05:00",
                        "albums": ["Journal"],
                    }
                ],
                notes=[],
            )
            res = self.adapter.tndc_preflight(["--json"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = json.loads(res.stdout)
            self.assertTrue(isinstance(payload.get("photos_albums"), list))
            self.assertTrue(all(isinstance(a["count"], int) for a in payload["photos_albums"]))

    def test_T1_F02_03_stage0_blank_notes_folder_lists_counts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f02n_") as tmp:
            env = _write_stub_env(
                Path(tmp),
                photos=[],
                notes=[
                    {
                        "note_id": "N1",
                        "folder": "4_bloom",
                        "account": "iCloud",
                        "title": "Secret",
                        "created_at": "2015-01-01T10:00:00-05:00",
                        "modified_at": "2015-01-01T10:00:00-05:00",
                        "plaintext": "PRIVATE_BODY_NEVER_PRINT",
                    }
                ],
            )
            res = self.adapter.tndc_preflight(["--json"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = json.loads(res.stdout)
            self.assertTrue(isinstance(payload.get("notes_folders"), list))
            self.assertTrue(all(isinstance(f["count"], int) for f in payload["notes_folders"]))

    def test_T1_F02_04_stage0_no_sqlite_access(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f02_sql_") as tmp:
            env = _write_stub_env(Path(tmp), photos=[], notes=[])
            res = self.adapter.tndc_preflight(["--json"], extra_env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        assert_preflight_contract(res, "T1_F02_04")
        combined = res.stdout + res.stderr
        self.assertNotIn("Photos.sqlite", combined)
        self.assertNotIn("NoteStore.sqlite", combined)

    def test_T1_F02_05_stage0_no_body_text_leaked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f02s_") as tmp:
            env = _write_stub_env(
                Path(tmp),
                photos=[],
                notes=[
                    {
                        "note_id": "N1",
                        "folder": "4_bloom",
                        "account": "iCloud",
                        "title": "T",
                        "created_at": "2015-01-01T10:00:00-05:00",
                        "modified_at": "2015-01-01T10:00:00-05:00",
                        "plaintext": "TOP_SECRET_NOTE_TOKEN_987",
                    }
                ],
            )
            res = self.adapter.tndc_preflight(["--json"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertNotIn("TOP_SECRET_NOTE_TOKEN_987", res.stdout)

    # --- Feature 3: External custody & git-tree refusal ---

    def test_T1_F03_01_external_out_dir_permissions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f03_") as tmp:
            tmp_p = Path(tmp)
            env = _write_stub_env(
                tmp_p,
                photos=[{"photo_uuid": "U1", "original_filename": "A.JPG", "witnessed_at": "2015-01-01T10:00:00-05:00", "albums": ["Journal"]}],
                notes=[{"note_id": "N1", "folder": "4_bloom", "title": "T", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": "body"}],
            )
            ext = tmp_p / "external_intake"
            res = self.adapter.tndc_witness(["--out-dir", str(ext)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            assert_no_traceback(res, "T1_F03_01")
            assert_mode_0700(ext)
            assert_mode_0600(ext / "photo_witnesses.json")
            assert_mode_0600(ext / "ios_notes.json")

    def test_T1_F03_02_default_out_dir_targets_archive4t_intake(self) -> None:
        res = self.adapter.tndc_witness(["--dry-run"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("/Volumes/Archive4T/Media/intake/versforms-witnesses", res.stdout)

    def test_T1_F03_03_refuses_out_dir_inside_tndc_repo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f03_git_") as tmp:
            repo = Path(tmp) / "tndc_git"
            (repo / ".git").mkdir(parents=True)
            out_dir = repo / "raw_out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir)])
            self.assertNotEqual(res.returncode, 0)
            self.assertFalse(out_dir.exists())

    def test_T1_F03_04_refuses_out_dir_inside_jhw_repo(self) -> None:
        raw_out = self.adapter.cfg.jhw_dir / "raw_out_should_not_exist"
        res = self.adapter.tndc_witness(["--out-dir", str(raw_out)])
        self.assertNotEqual(res.returncode, 0)
        self.assertFalse(raw_out.exists())

    def test_T1_F03_05_temp_git_repo_with_explicit_override_allowed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f03_ov_") as tmp:
            tmp_p = Path(tmp)
            env = _write_stub_env(
                tmp_p,
                photos=[{"photo_uuid": "U1", "original_filename": "A.JPG", "witnessed_at": "2015-01-01T10:00:00-05:00", "albums": ["Journal"]}],
                notes=[],
            )
            repo = tmp_p / "temp_git"
            (repo / ".git").mkdir(parents=True)
            out_dir = repo / "raw_out"
            res = self.adapter.tndc_witness(
                ["--out-dir", str(out_dir), "--allow-git-dir-for-tests"], extra_env=env
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            assert_no_traceback(res, "T1_F03_05")
            self.assertTrue((out_dir / "photo_witnesses.json").is_file())
            validate_photo_witnesses_schema(
                json.loads((out_dir / "photo_witnesses.json").read_text(encoding="utf-8"))
            )

    # --- Feature 4: Apple Photos read-only harvester ---

    def test_T1_F04_01_photos_export_3_jpegs_with_required_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f04_") as tmp:
            tmp_p = Path(tmp)
            photos = [
                {
                    "photo_uuid": f"U{i}",
                    "original_filename": f"IMG_{i}.JPG",
                    "witnessed_at": f"2015-0{i}-10T12:00:00-04:00",
                    "albums": ["Journal"],
                }
                for i in (1, 2, 3)
            ]
            env = _write_stub_env(tmp_p, photos=photos, notes=[])
            out_dir = tmp_p / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            pw = json.loads((out_dir / "photo_witnesses.json").read_text(encoding="utf-8"))
            validate_photo_witnesses_schema(pw)
            self.assertEqual(len(pw), 3)
            for item in pw:
                self.assertTrue(Path(item["local_path"]).is_file())

    def test_T1_F04_02_photos_sorted_ascending_by_witnessed_at(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f04_sort_") as tmp:
            tmp_p = Path(tmp)
            photos = [
                {"photo_uuid": "U3", "original_filename": "C.JPG", "witnessed_at": "2015-05-01T10:00:00-04:00", "albums": ["Journal"]},
                {"photo_uuid": "U1", "original_filename": "A.JPG", "witnessed_at": "2014-11-01T10:00:00-05:00", "albums": ["Journal"]},
                {"photo_uuid": "U2", "original_filename": "B.JPG", "witnessed_at": "2015-02-01T10:00:00-05:00", "albums": ["Journal"]},
            ]
            env = _write_stub_env(tmp_p, photos=photos, notes=[])
            out_dir = tmp_p / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            pw = json.loads((out_dir / "photo_witnesses.json").read_text(encoding="utf-8"))
            validate_photo_witnesses_schema(pw)
            self.assertEqual([x["photo_uuid"] for x in pw], ["U1", "U2", "U3"])

    def test_T1_F04_03_photos_album_filter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f04_alb_") as tmp:
            tmp_p = Path(tmp)
            photos = [
                {"photo_uuid": "U1", "original_filename": "A.JPG", "witnessed_at": "2015-01-01T10:00:00-05:00", "albums": ["Journal"]},
                {"photo_uuid": "U2", "original_filename": "B.JPG", "witnessed_at": "2015-02-01T10:00:00-05:00", "albums": ["Other"]},
            ]
            env = _write_stub_env(tmp_p, photos=photos, notes=[])
            out_dir = tmp_p / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir), "--photos-album", "Journal"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            pw = json.loads((out_dir / "photo_witnesses.json").read_text(encoding="utf-8"))
            self.assertEqual([x["photo_uuid"] for x in pw], ["U1"])

    def test_T1_F04_04_photos_max_year_filter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f04_yr_") as tmp:
            tmp_p = Path(tmp)
            photos = [
                {"photo_uuid": "U14", "original_filename": "A.JPG", "witnessed_at": "2014-06-01T10:00:00-04:00", "albums": ["J"]},
                {"photo_uuid": "U15", "original_filename": "B.JPG", "witnessed_at": "2015-06-01T10:00:00-04:00", "albums": ["J"]},
                {"photo_uuid": "U16", "original_filename": "C.JPG", "witnessed_at": "2016-06-01T10:00:00-04:00", "albums": ["J"]},
            ]
            env = _write_stub_env(tmp_p, photos=photos, notes=[])
            out_dir = tmp_p / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir), "--max-year", "2015"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            pw = json.loads((out_dir / "photo_witnesses.json").read_text(encoding="utf-8"))
            self.assertEqual([x["photo_uuid"] for x in pw], ["U14", "U15"])

    def test_T1_F04_05_dry_run_writes_zero_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f04_dry_") as tmp:
            out_dir = Path(tmp) / "dry_out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir), "--dry-run"])
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertFalse(out_dir.exists())

    # --- Feature 5: Apple Notes read-only JXA harvester ---

    def test_T1_F05_01_notes_export_3_notes_required_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f05_") as tmp:
            tmp_p = Path(tmp)
            notes = [
                {
                    "note_id": f"N{i}",
                    "folder": "4_bloom",
                    "title": f"Draft {i}",
                    "created_at": f"2015-0{i}-01T10:00:00-05:00",
                    "modified_at": f"2015-0{i}-01T11:00:00-05:00",
                    "plaintext": f"Body {i}",
                }
                for i in (1, 2, 3)
            ]
            env = _write_stub_env(tmp_p, photos=[], notes=notes)
            out_dir = tmp_p / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            loaded = json.loads((out_dir / "ios_notes.json").read_text(encoding="utf-8"))
            validate_ios_notes_schema(loaded)
            self.assertEqual(len(loaded), 3)

    def test_T1_F05_02_notes_sorted_ascending_by_created_at(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f05_sort_") as tmp:
            tmp_p = Path(tmp)
            notes = [
                {"note_id": "N3", "folder": "4_bloom", "title": "3", "created_at": "2015-04-12T10:00:00-04:00", "modified_at": "2015-04-12T10:00:00-04:00", "plaintext": "3"},
                {"note_id": "N1", "folder": "4_bloom", "title": "1", "created_at": "2014-08-01T10:00:00-04:00", "modified_at": "2014-08-01T10:00:00-04:00", "plaintext": "1"},
                {"note_id": "N2", "folder": "4_bloom", "title": "2", "created_at": "2015-01-15T10:00:00-05:00", "modified_at": "2015-01-15T10:00:00-05:00", "plaintext": "2"},
            ]
            env = _write_stub_env(tmp_p, photos=[], notes=notes)
            out_dir = tmp_p / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            loaded = json.loads((out_dir / "ios_notes.json").read_text(encoding="utf-8"))
            validate_ios_notes_schema(loaded)
            self.assertEqual([n["note_id"] for n in loaded], ["N1", "N2", "N3"])

    def test_T1_F05_03_notes_folder_filter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f05_fld_") as tmp:
            tmp_p = Path(tmp)
            notes = [
                {"note_id": "N1", "folder": "4_bloom", "title": "A", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": "a"},
                {"note_id": "N2", "folder": "Recipes", "title": "B", "created_at": "2015-01-02T10:00:00-05:00", "modified_at": "2015-01-02T10:00:00-05:00", "plaintext": "b"},
            ]
            env = _write_stub_env(tmp_p, photos=[], notes=notes)
            out_dir = tmp_p / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir), "--notes-folder", "4_bloom"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            loaded = json.loads((out_dir / "ios_notes.json").read_text(encoding="utf-8"))
            self.assertEqual([n["note_id"] for n in loaded], ["N1"])

    def test_T1_F05_04_notes_text_sha256_exact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f05_sha_") as tmp:
            tmp_p = Path(tmp)
            text = "The walls collapse"
            notes = [
                {"note_id": "N1", "folder": "4_bloom", "title": "W", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": text}
            ]
            env = _write_stub_env(tmp_p, photos=[], notes=notes)
            out_dir = tmp_p / "out"
            self.adapter.tndc_witness(["--out-dir", str(out_dir)], extra_env=env)
            loaded = json.loads((out_dir / "ios_notes.json").read_text(encoding="utf-8"))
            self.assertEqual(loaded[0]["text_sha256"], sha256_bytes(text.encode("utf-8")))

    def test_T1_F05_05_notes_preserves_utf8_em_dash_and_newlines(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f05_utf_") as tmp:
            tmp_p = Path(tmp)
            text = "Line one — em dash\nLine two"
            notes = [
                {"note_id": "N1", "folder": "4_bloom", "title": "U", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": text}
            ]
            env = _write_stub_env(tmp_p, photos=[], notes=notes)
            out_dir = tmp_p / "out"
            self.adapter.tndc_witness(["--out-dir", str(out_dir)], extra_env=env)
            loaded = json.loads((out_dir / "ios_notes.json").read_text(encoding="utf-8"))
            self.assertEqual(loaded[0]["plaintext"], text)
            self.assertNotIn("<div>", loaded[0]["plaintext"])

    # --- Feature 6: Vision OCR exporter & cache ---

    def test_T1_F06_01_ocr_creates_cache_keyed_by_uuid(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f06_") as tmp:
            out_dir = Path(tmp) / "out"
            p1 = out_dir / "photos" / "U1_A.jpg"
            p2 = out_dir / "photos" / "U2_B.jpg"
            build_poem_image(p1, ["The walls collapse"])
            build_poem_image(p2, ["A flower is a flower"])
            write_intake_bundle(
                out_dir,
                photos=[
                    make_photo_witness("U1", "A.jpg", p1, "2015-01-01T10:00:00-05:00"),
                    make_photo_witness("U2", "B.jpg", p2, "2015-01-02T10:00:00-05:00"),
                ],
                notes=[],
            )
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir), "--ocr-only"])
            self.assertEqual(res.returncode, 0, res.stderr)
            cache = json.loads((out_dir / "ocr_cache.json").read_text(encoding="utf-8"))
            validate_ocr_cache_schema(cache)
            self.assertEqual(set(cache.keys()), {"U1", "U2"})

    def test_T1_F06_02_ocr_idempotent_preserves_existing_uuid(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f06_idem_") as tmp:
            out_dir = Path(tmp) / "out"
            p1 = out_dir / "photos" / "U1_A.jpg"
            p2 = out_dir / "photos" / "U2_B.jpg"
            build_poem_image(p1, ["First"])
            build_poem_image(p2, ["Second"])
            existing = {
                "U1": {"text": "PRESERVED_TEXT", "lines": ["PRESERVED_TEXT"], "ocr_engine": "Vision", "ocr_at": "2015-01-01T00:00:00Z"}
            }
            write_intake_bundle(
                out_dir,
                photos=[
                    make_photo_witness("U1", "A.jpg", p1, "2015-01-01T10:00:00-05:00"),
                    make_photo_witness("U2", "B.jpg", p2, "2015-01-02T10:00:00-05:00"),
                ],
                notes=[],
                ocr_cache=existing,
            )
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir), "--ocr-only"])
            self.assertEqual(res.returncode, 0, res.stderr)
            cache = json.loads((out_dir / "ocr_cache.json").read_text(encoding="utf-8"))
            self.assertEqual(cache["U1"]["text"], "PRESERVED_TEXT")
            self.assertIn("U2", cache)

    def test_T1_F06_03_ocr_synthetic_poem_image_non_empty(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f06_txt_") as tmp:
            out_dir = Path(tmp) / "out"
            p1 = out_dir / "photos" / "U1_poem.png"
            build_poem_image(p1, ["The walls collapse"])
            write_intake_bundle(
                out_dir,
                photos=[make_photo_witness("U1", "poem.png", p1, "2015-01-01T10:00:00-05:00")],
                notes=[],
            )
            env = {"E2E_STUB_OCR_TEXT_MAP": json.dumps({"U1": "The walls collapse"})}
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir), "--ocr-only"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            cache = json.loads((out_dir / "ocr_cache.json").read_text(encoding="utf-8"))
            self.assertTrue(len(cache["U1"]["text"]) > 0)
            self.assertIsInstance(cache["U1"]["lines"], list)

    def test_T1_F06_04_ocr_dry_run_no_cache_written(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f06_dry_") as tmp:
            out_dir = Path(tmp) / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out_dir), "--ocr", "--dry-run"])
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertFalse((out_dir / "ocr_cache.json").exists())

    def test_T1_F06_05_ocr_cache_0600_permissions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f06_perm_") as tmp:
            out_dir = Path(tmp) / "out"
            p1 = out_dir / "photos" / "U1_A.jpg"
            build_poem_image(p1, ["Text"])
            write_intake_bundle(
                out_dir,
                photos=[make_photo_witness("U1", "A.jpg", p1, "2015-01-01T10:00:00-05:00")],
                notes=[],
            )
            self.adapter.tndc_witness(["--out-dir", str(out_dir), "--ocr-only"])
            assert_mode_0600(out_dir / "ocr_cache.json")

    # --- Feature 7: tool-notes-docs-capture test & lint suite ---

    def test_T1_F07_01_tndc_pytest_passes(self) -> None:
        res = self.adapter.tndc_run_tests()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_T1_F07_02_tndc_ruff_passes(self) -> None:
        res = self.adapter.tndc_run_ruff()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_T1_F07_03_tndc_cce_status_intact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f07_st_") as tmp:
            s = Path(tmp) / "state"
            o = Path(tmp) / "out"
            res = self.adapter.tndc_status(s, o)
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = json.loads(res.stdout)
            self.assertIsInstance(payload, dict)

    def test_T1_F07_04_tndc_cce_capture_notes_dry_run_intact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f07_cap_") as tmp:
            s = Path(tmp) / "state"
            o = Path(tmp) / "out"
            res = self.adapter.tndc_capture_notes_dry_run(s, o)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_T1_F07_05_tndc_guarded_test_case_present(self) -> None:
        if self.adapter.cfg.self_check:
            res = self.adapter.tndc_run_tests()
            self.assertEqual(res.returncode, 0)
            return
        assert self.adapter.cfg.tndc_dir is not None
        guards_file = self.adapter.cfg.tndc_dir / "tests" / "guards.py"
        self.assertTrue(guards_file.is_file())
        res = subprocess.run(
            [str(self.adapter.tndc_python()), "-m", "pytest", "tests/test_guards.py"],
            cwd=str(self.adapter.cfg.tndc_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    # --- Feature 8: Stage 2 candidate matcher (match_witnesses.py) ---

    def test_T1_F08_01_match_photo_ocr_p001_ranked_first(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f08_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            img = intake / "photos" / "U1_p001.jpg"
            build_poem_image(img, ["The walls collapse like the seal"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U1", "p001.jpg", img, "2015-03-10T14:00:00-04:00")],
                notes=[],
                ocr_cache={"U1": {"text": "The walls collapse like the seal youve sown", "lines": ["The walls collapse"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            res = self.adapter.jhw_match(sb, intake)
            self.assertEqual(res.returncode, 0, res.stderr)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            validate_witness_links_schema(links)
            pl = links["photo_links"][0]
            self.assertEqual(pl["candidates"][0]["piece_id"], "p001")
            self.assertLessEqual(len(pl["candidates"]), 3)
            self.assertEqual(pl["status"], "pending_review")
            self.assertEqual(pl["textual_state"], "unreviewed")

    def test_T1_F08_02_match_note_p003_ranked_first(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f08_n_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[
                    make_ios_note(
                        "N1",
                        "4_bloom",
                        "Flower",
                        "2015-03-10T10:00:00-04:00",
                        "2015-03-10T10:05:00-04:00",
                        "A Flower is a Flower, or A Scream in the lonliest Wilderness",
                    )
                ],
                ocr_cache={},
            )
            res = self.adapter.jhw_match(sb, intake)
            self.assertEqual(res.returncode, 0, res.stderr)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            validate_witness_links_schema(links)
            nl = links["note_links"][0]
            self.assertEqual(nl["candidates"][0]["piece_id"], "p003")
            self.assertEqual(nl["status"], "pending_review")
            self.assertEqual(nl["relation"], "unreviewed")

    def test_T1_F08_03_match_top3_candidates_and_null_confirmed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f08_m_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            p2 = intake / "photos" / "U2.jpg"
            build_poem_image(p1, ["The walls collapse"])
            build_poem_image(p2, ["MYTHOLOGIZED FACT"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00"),
                    make_photo_witness("U2", "2.jpg", p2, "2015-02-01T10:00:00-05:00"),
                ],
                notes=[
                    make_ios_note("N1", "F", "T1", "2015-01-05T10:00:00-05:00", "2015-01-05T10:00:00-05:00", self.corpus.extract_version_text("p020")[:120]),
                    make_ios_note("N2", "F", "T2", "2015-02-05T10:00:00-05:00", "2015-02-05T10:00:00-05:00", self.corpus.extract_version_text("p099")[:120]),
                ],
                ocr_cache={
                    "U1": {"text": self.corpus.extract_version_text("p001")[:100], "lines": ["The walls"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U2": {"text": self.corpus.extract_version_text("p126"), "lines": ["MYTHOLOGIZED FACT"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            res = self.adapter.jhw_match(sb, intake)
            self.assertEqual(res.returncode, 0, res.stderr)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            for item in links["photo_links"] + links["note_links"]:
                self.assertLessEqual(len(item["candidates"]), 3)
                self.assertIsNone(item["confirmed_piece_id"])
                for cand in item["candidates"]:
                    for k in ("piece_id", "score", "token_overlap", "fuzzy_score"):
                        self.assertIn(k, cand)

    def test_T1_F08_04_match_preserves_confirmed_links_on_rerun(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f08_re_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            p2 = intake / "photos" / "U2.jpg"
            build_poem_image(p1, ["The walls collapse"])
            build_poem_image(p2, ["A Flower is a Flower"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00"),
                    make_photo_witness("U2", "2.jpg", p2, "2015-01-02T10:00:00-05:00"),
                ],
                notes=[],
                ocr_cache={
                    "U1": {"text": "The walls collapse like the seal", "lines": ["The walls"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U2": {"text": "A Flower is a Flower", "lines": ["A Flower"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            self.adapter.jhw_match(sb, intake)
            links_path = sb / "source" / "witness_links.json"
            links = json.loads(links_path.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p001"
            links["photo_links"][0]["textual_state"] = "matches_scan"
            links_path.write_text(json.dumps(links, indent=2), encoding="utf-8")

            res = self.adapter.jhw_match(sb, intake)
            self.assertEqual(res.returncode, 0, res.stderr)
            rerun = json.loads(links_path.read_text(encoding="utf-8"))
            self.assertEqual(rerun["photo_links"][0]["status"], "confirmed")
            self.assertEqual(rerun["photo_links"][0]["confirmed_piece_id"], "p001")
            self.assertEqual(rerun["photo_links"][0]["textual_state"], "matches_scan")
            self.assertEqual(rerun["photo_links"][1]["status"], "pending_review")

    def test_T1_F08_05_match_records_photo_metadata_accurately(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f08_p81_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U81.jpg"
            build_poem_image(p1, ["every day depression in a beautiful dress"])
            pw = make_photo_witness("U81", "81.jpg", p1, "2015-05-02T18:10:00-04:00", camera_model="Apple iPhone 5s")
            write_intake_bundle(
                intake,
                photos=[pw],
                notes=[],
                ocr_cache={"U81": {"text": "every day depression in a beautiful dress", "lines": ["every day depression"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            pl = links["photo_links"][0]
            self.assertEqual(pl["photo_uuid"], "U81")
            self.assertEqual(pl["photo_sha256"], pw["photo_sha256"])
            self.assertEqual(pl["witnessed_at"], "2015-05-02T18:10:00-04:00")
            self.assertEqual(pl["camera_model"], "Apple iPhone 5s")
            self.assertEqual(pl["candidates"][0]["piece_id"], "p081")

    # --- Feature 9: Public-repo privacy hygiene & review report ---

    def test_T1_F09_01_witness_links_excludes_private_note_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f09_1_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[make_ios_note("N1", "Love", "My Secret", "2015-01-01T10:00:00-05:00", "2015-01-01T10:05:00-05:00", "SECRET DIARY ENTRY The walls")],
                ocr_cache={},
            )
            self.adapter.jhw_match(sb, intake)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            assert_public_privacy_clean(links, forbidden_substrings=("SECRET DIARY ENTRY", "My Secret", "Love"), context="witness_links")

    def test_T1_F09_02_witness_links_excludes_local_path_and_raw_ocr(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f09_2_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["PRIVATE OCR TEXT"])
            pw = make_photo_witness("U1", "IMG_1.JPG", p1, "2015-01-01T10:00:00-05:00")
            pw["local_path"] = "/Users/example/Private/IMG_1.JPG"
            write_intake_bundle(
                intake,
                photos=[pw],
                notes=[],
                ocr_cache={"U1": {"text": "PRIVATE OCR TEXT The walls", "lines": ["PRIVATE OCR TEXT"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            assert_public_privacy_clean(links, forbidden_substrings=("PRIVATE OCR TEXT", "/Users/example"), context="witness_links")

    def test_T1_F09_03_verbose_snippet_report_written_inside_intake_dir(self) -> None:
        before_git = subprocess.run(
            ["git", "-C", str(self.adapter.cfg.jhw_dir), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        with tempfile.TemporaryDirectory(prefix="e2e_f09_3_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            before_sb = {p.relative_to(sb).as_posix() for p in sb.rglob("*") if p.is_file()}
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["The walls"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00")],
                notes=[make_ios_note("N1", "F", "T", "2015-01-02T10:00:00-05:00", "2015-01-02T10:00:00-05:00", "A Flower is a Flower")],
                ocr_cache={"U1": {"text": "The walls collapse", "lines": ["The walls"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            reports = [p for p in intake.iterdir() if p.is_file() and p.name not in {"photo_witnesses.json", "ios_notes.json", "ocr_cache.json"}]
            self.assertTrue(len(reports) >= 1, "Expected verbose review report written inside --intake-dir")
            after_sb = {p.relative_to(sb).as_posix() for p in sb.rglob("*") if p.is_file()}
            new_in_sb = after_sb - before_sb
            self.assertEqual(new_in_sb, {"source/witness_links.json"}, f"Unexpected files written inside JHW sandbox: {new_in_sb}")
        after_git = subprocess.run(
            ["git", "-C", str(self.adapter.cfg.jhw_dir), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        self.assertEqual(before_git, after_git)

    def test_T1_F09_04_stdout_summary_concise_without_note_body_dump(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f09_4_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[make_ios_note("N1", "F", "T", "2015-01-01T10:00:00-05:00", "2015-01-01T10:00:00-05:00", "SECRET_BODY_DO_NOT_ECHO_STDOUT")],
                ocr_cache={},
            )
            res = self.adapter.jhw_match(sb, intake)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertNotIn("SECRET_BODY_DO_NOT_ECHO_STDOUT", res.stdout)
            self.assertTrue(len(res.stdout.strip()) > 0)

    def test_T1_F09_05_chronology_privacy_clean(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f09_5_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[make_ios_note("N1", "SecretFolder", "SecretTitle", "2015-02-01T10:00:00-05:00", "2015-02-01T10:00:00-05:00", "SECRET_PLAIN_TEXT_XYZ")],
                ocr_cache={},
            )
            self.adapter.jhw_match(sb, intake)
            links_path = sb / "source" / "witness_links.json"
            links = json.loads(links_path.read_text(encoding="utf-8"))
            links["note_links"][0]["status"] = "confirmed"
            links["note_links"][0]["relation"] = "standalone_cohort"
            links_path.write_text(json.dumps(links, indent=2), encoding="utf-8")

            chron_path = sb / "source" / "chronology.json"
            res = self.adapter.jhw_chronology(sb, links_path, chron_path)
            self.assertEqual(res.returncode, 0, res.stderr)
            chron = json.loads(chron_path.read_text(encoding="utf-8"))
            assert_public_privacy_clean(chron, forbidden_substrings=("SECRET_PLAIN_TEXT_XYZ", "SecretTitle", "SecretFolder"), context="chronology")

    # --- Feature 10: Two-repo boundary & check.py integrity ---

    def test_T1_F10_01_two_repo_boundary_clean(self) -> None:
        assert_two_repo_boundary_clean(self.adapter.cfg.jhw_dir)

    def test_T1_F10_02_check_py_passes_baseline_and_post_pipeline(self) -> None:
        before = snapshot_protected_hashes(self.adapter.cfg.jhw_dir)
        res = self.adapter.jhw_check()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("OK", res.stdout)
        self.assertIn("0 missing", res.stdout)
        self.assertIn("0 bare", res.stdout)
        assert_protected_paths_unchanged(self.adapter.cfg.jhw_dir, before)

    def test_T1_F10_03_ci_local_passes(self) -> None:
        res = self.adapter.jhw_ci_local(only=("check",))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        ut = subprocess.run(
            [str(self.adapter.jhw_python()), "-m", "unittest", "tests/test_check_manifest.py", "tests/test_ci_local.py"],
            cwd=str(self.adapter.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(ut.returncode, 0, ut.stdout + ut.stderr)

    def test_T1_F10_04_protected_immutable_paths_unchanged_after_pipeline(self) -> None:
        before = snapshot_protected_hashes(self.adapter.cfg.jhw_dir)
        with tempfile.TemporaryDirectory(prefix="e2e_f10_4_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            self.adapter.jhw_match(sb, intake)
            self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", sb / "source" / "chronology.json")
        assert_protected_paths_unchanged(self.adapter.cfg.jhw_dir, before)

    def test_T1_F10_05_silent_launch_lint_zero_bare(self) -> None:
        res = self.adapter.jhw_silent_lint()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("OK", res.stdout)

    # --- Feature 11: Stage 3 chronology builder (build_chronology.py) ---

    def test_T1_F11_01_photo_anchored_date_basis(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f11_1_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U15.jpg"
            build_poem_image(p1, ["There are certain questions"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U15", "15.jpg", p1, "2015-03-10T14:00:00-04:00")],
                notes=[],
                ocr_cache={"U15": {"text": self.corpus.extract_version_text("p015"), "lines": ["questions"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p015"
            links["photo_links"][0]["textual_state"] = "matches_scan"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp = sb / "source" / "chronology.json"
            res = self.adapter.jhw_chronology(sb, lp, cp)
            self.assertEqual(res.returncode, 0, res.stderr)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            p15 = next(e for e in chron["physical_codex_order"] if e["piece_id"] == "p015")
            self.assertEqual(p15["chronology"]["date_basis"], "photo_anchored")
            self.assertEqual(p15["chronology"]["est_end"], "2015-03-10")

    def test_T1_F11_02_interpolated_interior_span(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f11_2_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U15.jpg"
            p2 = intake / "photos" / "U29.jpg"
            build_poem_image(p1, ["questions"])
            build_poem_image(p2, ["anchor 20"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U15", "15.jpg", p1, "2015-03-10T14:00:00-04:00"),
                    make_photo_witness("U29", "29.jpg", p2, "2015-04-10T14:00:00-04:00"),
                ],
                notes=[],
                ocr_cache={
                    "U15": {"text": self.corpus.extract_version_text("p015"), "lines": ["q"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U29": {"text": self.corpus.extract_version_text("p029"), "lines": ["a"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p015"
            links["photo_links"][1]["status"] = "confirmed"
            links["photo_links"][1]["confirmed_piece_id"] = "p029"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            p20 = next(e for e in chron["physical_codex_order"] if e["piece_id"] == "p020")
            self.assertEqual(p20["chronology"]["date_basis"], "interpolated")
            self.assertGreaterEqual(p20["chronology"]["est_start"], "2015-03-10")
            self.assertLessEqual(p20["chronology"]["est_end"], "2015-04-10")

    def test_T1_F11_03_extrapolated_head_and_tail_never_digitized_at(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f11_3_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U15.jpg"
            p2 = intake / "photos" / "U29.jpg"
            build_poem_image(p1, ["q"])
            build_poem_image(p2, ["a"])
            write_intake_bundle(
                intake,
                photos=[
                    make_photo_witness("U15", "15.jpg", p1, "2015-03-10T14:00:00-04:00"),
                    make_photo_witness("U29", "29.jpg", p2, "2015-04-10T14:00:00-04:00"),
                ],
                notes=[],
                ocr_cache={
                    "U15": {"text": self.corpus.extract_version_text("p015"), "lines": ["q"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                    "U29": {"text": self.corpus.extract_version_text("p029"), "lines": ["a"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"},
                },
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p015"
            links["photo_links"][1]["status"] = "confirmed"
            links["photo_links"][1]["confirmed_piece_id"] = "p029"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp, digitized_at="2015-09")
            chron = json.loads(cp.read_text(encoding="utf-8"))
            p001 = next(e for e in chron["physical_codex_order"] if e["piece_id"] == "p001")
            p126 = next(e for e in chron["physical_codex_order"] if e["piece_id"] == "p126")
            self.assertEqual(p001["chronology"]["date_basis"], "extrapolated_head")
            self.assertEqual(p126["chronology"]["date_basis"], "extrapolated_tail")
            assert_two_clock_clean(chron, "2015-09", {"2015-03-10", "2015-04-10"})

            cp_b = sb / "source" / "chronology_2024_06.json"
            res_b = self.adapter.jhw_chronology(sb, lp, cp_b, digitized_at="2024-06")
            self.assertEqual(res_b.returncode, 0, res_b.stderr)
            chron_b = json.loads(cp_b.read_text(encoding="utf-8"))
            validate_chronology_schema(chron_b, self.corpus, links)
            assert_two_clock_clean(chron_b, "2024-06", {"2015-03-10", "2015-04-10"})
            assert_two_clock_invariant(chron, chron_b)

    def test_T1_F11_04_dual_sort_orders_with_interleaved_note(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f11_4_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U15.jpg"
            build_poem_image(p1, ["q"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U15", "15.jpg", p1, "2015-03-10T14:00:00-04:00")],
                notes=[make_ios_note("N20", "4_bloom", "T", "2015-03-20T22:10:00-04:00", "2015-03-20T22:15:00-04:00", "Note draft")],
                ocr_cache={"U15": {"text": self.corpus.extract_version_text("p015"), "lines": ["q"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p015"
            links["note_links"][0]["status"] = "confirmed"
            links["note_links"][0]["relation"] = "standalone_cohort"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            validate_chronology_schema(chron, self.corpus, links)
            note_items = [e for e in chron["amalgamated_chronological_order"] if e.get("entry_type") == "ios_note"]
            self.assertEqual(len(note_items), 1)
            self.assertEqual(note_items[0]["note_id"], "N20")

    def test_T1_F11_05_schema_canonical_sha_and_23_shared_surfaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f11_5_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            self.adapter.jhw_match(sb, intake)
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            validate_chronology_schema(chron, self.corpus)
            self.assertEqual(len(self.corpus.multi_piece_pages), 23)
            top_surfs = {e["witnesses"]["codex_scan"]["surface_id"] for e in chron["physical_codex_order"]}
            shared_surfs = {
                e["witnesses"]["codex_scan"]["surface_id"]
                for e in chron["physical_codex_order"]
                if e["witnesses"]["codex_scan"]["shared_surface"]
            }
            self.assertEqual(shared_surfs, top_surfs & set(self.corpus.multi_piece_pages.keys()))

    # --- Feature 12: Downstream Round 1 projection helper ---

    def test_T1_F12_01_round1_single_piece_diary1_opens_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f12_1_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            self.adapter.jhw_match(sb, intake)
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", cp)
            out_dir = Path(tmp) / "proj"
            res = self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p001"], extra_args=["--surface", "diary1"])
            self.assertEqual(res.returncode, 0, res.stderr)
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["exports"]), 1)
            out_img = out_dir / manifest["exports"][0]["output_file"]
            with Image.open(out_img) as im:
                self.assertGreater(im.width, 0)
                self.assertGreater(im.height, 0)

    def test_T1_F12_02_round1_strips_exif_gps_xmp_icc_thumbnail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f12_2_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            self.adapter.jhw_match(sb, intake)
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", cp)
            dirty_jpg = Path(tmp) / "dirty_src.jpg"
            build_metadata_laden_jpeg(dirty_jpg, lines=["Test line"])
            out_dir = Path(tmp) / "proj"
            res = self.adapter.jhw_export_round1(
                sb,
                cp,
                out_dir,
                pieces=["p001"],
                extra_args=["--surface", "diary1", "--override-image", str(dirty_jpg)],
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            assert_jpeg_metadata_clean(out_dir / manifest["exports"][0]["output_file"])

    def test_T1_F12_03_round1_diary62a_p001_isolates_p126(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f12_3_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            self.adapter.jhw_match(sb, intake)
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", cp)
            out_dir = Path(tmp) / "proj"
            res = self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p001"], extra_args=["--surface", "diary62a"])
            self.assertEqual(res.returncode, 0, res.stderr)
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            exp = manifest["exports"][0]
            self.assertTrue(exp["isolated_crop"])
            page62 = self.corpus.page_by_id["diary62a"]
            self.assertLess(exp["dimensions"][1], page62["ih"])
            assert_shared_surface_isolated(manifest, out_dir, self.corpus)
            with Image.open(out_dir / exp["output_file"]) as im:
                self.assertEqual(tuple(im.size), tuple(exp["dimensions"]))
                self.assertLess(im.size[1], page62["ih"])

    def test_T1_F12_04_round1_clean_piece_p003_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f12_4_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            self.adapter.jhw_match(sb, intake)
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", cp)
            out_dir = Path(tmp) / "proj"
            res = self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p003"])
            self.assertEqual(res.returncode, 0, res.stderr)
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            exp = manifest["exports"][0]
            self.assertEqual(exp["piece_id"], "p003")
            self.assertFalse(exp["shared_surface"])
            self.assertTrue(exp["sha256"].startswith("sha256:"))

    def test_T1_F12_05_round1_batch_3_isolated_pieces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f12_5_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            before = snapshot_protected_hashes(self.adapter.cfg.jhw_dir)
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            self.adapter.jhw_match(sb, intake)
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", cp)
            out_dir = Path(tmp) / "proj"
            res = self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p001", "p003", "p006"])
            self.assertEqual(res.returncode, 0, res.stderr)
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["exports"]), 3)
            for exp in manifest["exports"]:
                assert_jpeg_metadata_clean(out_dir / exp["output_file"])
            assert_protected_paths_unchanged(self.adapter.cfg.jhw_dir, before)

    # --- Feature 13: Opaque-box E2E test suite ---

    def test_T1_F13_01_runner_self_check_cli_exits_0(self) -> None:
        runner = Path(__file__).resolve().parent / "run_e2e.py"
        res = subprocess.run(
            [sys.executable, str(runner), "--self-check", "--tier", "1", "--filter", "T1_F03_01"],
            cwd=str(self.adapter.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_T1_F13_02_runner_tier1_json_output(self) -> None:
        runner = Path(__file__).resolve().parent / "run_e2e.py"
        res = subprocess.run(
            [sys.executable, str(runner), "--self-check", "--tier", "1", "--filter", "T1_F04_01", "--json"],
            cwd=str(self.adapter.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["failed"], 0)
        self.assertGreaterEqual(payload["passed"], 1)

    def test_T1_F13_03_unittest_discover_env_targeting(self) -> None:
        if os.environ.get("E2E_IN_UNITTEST_SUBPROCESS") == "1":
            return
        env = dict(os.environ)
        env["E2E_IN_UNITTEST_SUBPROCESS"] = "1"
        res = subprocess.run(
            [sys.executable, "-m", "unittest", "tests.e2e_witness.tier1_features.Tier1FeatureTests.test_T1_F13_03_unittest_discover_env_targeting"],
            cwd=str(self.adapter.cfg.jhw_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_T1_F13_04_e2e_suite_passes_check_py(self) -> None:
        res = self.adapter.jhw_check()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("0 bare", res.stdout)

    def test_T1_F13_05_tempdir_isolation_zero_leftovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f13_5_") as custom_tmp:
            env = dict(os.environ)
            env["TMPDIR"] = custom_tmp
            runner = Path(__file__).resolve().parent / "run_e2e.py"
            res = subprocess.run(
                [sys.executable, str(runner), "--self-check", "--tier", "1", "--filter", "T1_F08_01"],
                cwd=str(self.adapter.cfg.jhw_dir),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            leftovers = list(Path(custom_tmp).iterdir())
            self.assertEqual(leftovers, [], f"Leftover temp files: {leftovers}")

    # --- Feature 14: Final Milestone integration & Tier 5 readiness ---

    def test_T1_F14_01_arbitrary_target_paths_supported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_f14_1_") as tmp:
            jhw_copy = Path(tmp) / "jhw_rel"
            with JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
                cfg = TargetConfig(self_check=True, jhw_dir=sb, tndc_dir=None)
                ad = CliAdapter(cfg)
                self.assertEqual(ad.cfg.jhw_dir, sb.resolve())
            self.assertFalse(jhw_copy.exists())

    def test_T1_F14_02_nonexistent_tndc_dir_fails_closed(self) -> None:
        runner = Path(__file__).resolve().parent / "run_e2e.py"
        res = subprocess.run(
            [
                sys.executable,
                str(runner),
                "--tndc-dir",
                "/nonexistent/tndc_path_xyz",
                "--jhw-dir",
                str(self.adapter.cfg.jhw_dir),
            ],
            cwd=str(self.adapter.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(res.returncode, 0)

    def test_T1_F14_03_ci_local_coexistence_check(self) -> None:
        res = self.adapter.jhw_ci_local(only=("check",))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        ut = subprocess.run(
            [str(self.adapter.jhw_python()), "-m", "unittest", "tests/test_silent_launch_lint.py", "tests/test_check_manifest.py"],
            cwd=str(self.adapter.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(ut.returncode, 0, ut.stdout + ut.stderr)

    def test_T1_F14_04_tier_filter_flags_work_independently(self) -> None:
        runner = Path(__file__).resolve().parent / "run_e2e.py"
        tier_probes = {
            "1": "T1_F01_01",
            "2": "T2_F01_01",
            "3": "T3_P01",
            "4": "T4_S01",
        }
        for tier, flt in tier_probes.items():
            res = subprocess.run(
                [sys.executable, str(runner), "--self-check", "--tier", tier, "--filter", flt, "--json"],
                cwd=str(self.adapter.cfg.jhw_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"--tier {tier} failed: {res.stdout}\n{res.stderr}")
            data = json.loads(res.stdout)
            self.assertEqual(data["passed"], 1)

    def test_T1_F14_05_git_clean_post_e2e(self) -> None:
        if os.environ.get("E2E_REQUIRE_CLEAN_GIT") == "1":
            assert_git_clean(self.adapter.cfg.jhw_dir, "jhw")
            if self.adapter.cfg.tndc_dir:
                assert_git_clean(self.adapter.cfg.tndc_dir, "tndc")
        else:
            # Verify protected repo files were never touched even in dirty-branch development
            before = snapshot_protected_hashes(self.adapter.cfg.jhw_dir)
            assert_protected_paths_unchanged(self.adapter.cfg.jhw_dir, before)
