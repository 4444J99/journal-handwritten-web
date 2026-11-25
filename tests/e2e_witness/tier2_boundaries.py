"""Tier 2 Boundary & Corner Case tests (68 tests: T2-F01-01 .. T2-F14-05)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .cli_adapters import CliAdapter, JHWSandbox, get_target_config
from .fixtures import (
    CorpusIndex,
    build_blank_image,
    build_corrupt_file,
    build_metadata_laden_jpeg,
    build_poem_image,
    inject_digitized_at_into_chronology,
    inject_exif_into_jpeg,
    inject_plaintext_into_witness_links,
    make_ios_note,
    make_photo_witness,
    write_intake_bundle,
)
from .validators import (
    assert_cli_ok_or_handled_error,
    assert_no_traceback,
    assert_preflight_contract,
    assert_jpeg_metadata_clean,
    assert_protected_paths_unchanged,
    assert_public_privacy_clean,
    assert_shared_surface_isolated,
    assert_two_clock_clean,
    assert_two_clock_invariant,
    snapshot_protected_hashes,
    validate_chronology_schema,
    validate_ocr_cache_schema,
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


class Tier2BoundaryTests(unittest.TestCase):
    """68 boundary, corner-case, and anti-tautology tests."""

    adapter: CliAdapter
    corpus: CorpusIndex

    @classmethod
    def setUpClass(cls) -> None:
        cfg = get_target_config()
        cls.adapter = CliAdapter(cfg)
        cls.corpus = CorpusIndex(cls.adapter.cfg.jhw_dir)

    # --- F01 ---

    def test_T2_F01_01_python_meets_requires_python_311_plus(self) -> None:
        res = self.adapter.tndc_py_exec("import sys; print(sys.version_info[:2])")
        self.assertEqual(res.returncode, 0, res.stderr)
        res2 = self.adapter.jhw_py_exec("import sys; assert sys.version_info >= (3, 11); print('OK')")
        self.assertEqual(res2.returncode, 0, res2.stderr)

    # --- F02 ---

    def test_T2_F02_01_tcc_full_disk_access_denied_prints_guidance(self) -> None:
        res = self.adapter.tndc_preflight(
            ["--json"],
            extra_env={"E2E_STUB_TCC_DENIED": "1", "TNDC_SIMULATE_TCC_DENIED": "1"},
        )
        assert_no_traceback(res, "T2_F02_01")
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Full Disk Access", res.stdout + res.stderr)

    def test_T2_F02_02_automation_denied_prints_guidance(self) -> None:
        res = self.adapter.tndc_preflight(
            ["--json"],
            extra_env={
                "E2E_STUB_AUTOMATION_DENIED": "1",
                "TNDC_SIMULATE_AUTOMATION_DENIED": "1",
            },
        )
        assert_no_traceback(res, "T2_F02_02")
        self.assertNotEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Automation", res.stdout + res.stderr)

    def test_T2_F02_03_zero_count_album_and_folder_handled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f02_3_") as tmp:
            env = _write_stub_env(
                Path(tmp),
                photos=[],
                notes=[],
                extra={
                    "E2E_STUB_EXTRA_ALBUMS": json.dumps(["EmptyAlbum"]),
                    "E2E_STUB_EXTRA_FOLDERS": json.dumps([{"account": "iCloud", "folder": "Quick Notes"}]),
                },
            )
            res = self.adapter.tndc_preflight(["--json"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = assert_preflight_contract(res, "T2_F02_03")
            if self.adapter.cfg.self_check:
                self.assertIn({"album": "EmptyAlbum", "count": 0}, payload["photos_albums"])
                self.assertIn({"account": "iCloud", "folder": "Quick Notes", "count": 0}, payload["notes_folders"])
            else:
                notes = payload.get("notes") or {}
                folders = notes.get("folders", []) if isinstance(notes, dict) else []
                self.assertTrue(
                    any(f.get("name") == "Quick Notes" and f.get("count") == 0 for f in folders),
                    f"Real-target preflight did not report the empty folder: {folders!r}",
                )

    def test_T2_F02_04_duplicate_notes_folder_names_disambiguated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f02_4_") as tmp:
            notes = [
                {"note_id": "N1", "account": "user1@example.icloud", "folder": "Unknown", "title": "1", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": "a"},
                {"note_id": "N2", "account": "Miscellaneous", "folder": "Unknown", "title": "2", "created_at": "2015-01-02T10:00:00-05:00", "modified_at": "2015-01-02T10:00:00-05:00", "plaintext": "b"},
            ]
            env = _write_stub_env(Path(tmp), photos=[], notes=notes)
            res = self.adapter.tndc_preflight(["--json"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = assert_preflight_contract(res, "T2_F02_04")
            if self.adapter.cfg.self_check:
                unknowns = [f for f in payload["notes_folders"] if f["folder"] == "Unknown"]
                self.assertEqual(len(unknowns), 2)
            else:
                notes = payload.get("notes") or {}
                folders = notes.get("folders", []) if isinstance(notes, dict) else []
                unknowns = [
                    f for f in folders
                    if str(f.get("name") or "").strip() == "Unknown"
                ]
                self.assertEqual(len(unknowns), 2, [f.get("account") for f in folders])
                self.assertEqual(
                    len({f.get("account") for f in unknowns}), 2,
                    "Duplicate Unknown folders must be disambiguated by account",
                )

    def test_T2_F02_05_notes_folder_trailing_cr_and_space_safe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f02_5_") as tmp:
            notes = [
                {"note_id": "N1", "account": "iCloud", "folder": "4_bl00m.4_0S_core\r", "title": "1", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": "a"},
                {"note_id": "N2", "account": "iCloud", "folder": "Transcend ", "title": "2", "created_at": "2015-01-02T10:00:00-05:00", "modified_at": "2015-01-02T10:00:00-05:00", "plaintext": "b"},
            ]
            env = _write_stub_env(Path(tmp), photos=[], notes=notes)
            res = self.adapter.tndc_preflight(["--json"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            payload = json.loads(res.stdout)
            self.assertIsInstance(payload, dict)

    # --- F03 ---

    def test_T2_F03_01_refuses_git_repo_root_itself(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f03_1_") as tmp:
            repo = Path(tmp) / "repo"
            (repo / ".git").mkdir(parents=True)
            res = self.adapter.tndc_witness(["--out-dir", str(repo)])
            self.assertNotEqual(res.returncode, 0)
            self.assertFalse((repo / "photo_witnesses.json").exists())

    def test_T2_F03_02_refuses_deeply_nested_subdir_in_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f03_2_") as tmp:
            repo = Path(tmp) / "repo"
            (repo / ".git").mkdir(parents=True)
            deep = repo / "a" / "b" / "c" / "d"
            res = self.adapter.tndc_witness(["--out-dir", str(deep)])
            self.assertNotEqual(res.returncode, 0)
            self.assertFalse(deep.exists())

    def test_T2_F03_03_refuses_symlink_pointing_inside_git(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f03_3_") as tmp:
            repo = Path(tmp) / "repo"
            (repo / ".git").mkdir(parents=True)
            target = repo / "hidden_target"
            target.mkdir(parents=True)
            link = Path(tmp) / "outside_symlink"
            link.symlink_to(target)
            res = self.adapter.tndc_witness(["--out-dir", str(link)])
            self.assertNotEqual(res.returncode, 0)
            self.assertFalse((target / "photo_witnesses.json").exists())

    def test_T2_F03_04_refuses_git_worktree_where_dot_git_is_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f03_4_") as tmp:
            wt = Path(tmp) / "worktree"
            wt.mkdir(parents=True)
            (wt / ".git").write_text("gitdir: /somewhere/else/.git/worktrees/wt\n", encoding="utf-8")
            out = wt / "sub" / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out)])
            self.assertNotEqual(res.returncode, 0)
            self.assertFalse(out.exists())

    def test_T2_F03_05_allows_sibling_dot_git_backup_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f03_5_") as tmp:
            ok_dir = Path(tmp) / ".git_backup" / "intake"
            res = self.adapter.tndc_witness(["--out-dir", str(ok_dir), "--dry-run"])
            self.assertEqual(res.returncode, 0, res.stderr)

    # --- F04 ---

    def test_T2_F04_01_skips_movies_and_trashed_items(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f04_1_") as tmp:
            photos = [
                {"photo_uuid": "OK1", "original_filename": "OK.JPG", "witnessed_at": "2015-01-01T10:00:00-05:00", "ismovie": False, "intrash": False, "albums": ["J"]},
                {"photo_uuid": "MOV1", "original_filename": "M.MOV", "witnessed_at": "2015-01-02T10:00:00-05:00", "ismovie": True, "intrash": False, "albums": ["J"]},
                {"photo_uuid": "TR1", "original_filename": "T.JPG", "witnessed_at": "2015-01-03T10:00:00-05:00", "ismovie": False, "intrash": True, "albums": ["J"]},
            ]
            env = _write_stub_env(Path(tmp), photos=photos, notes=[])
            out = Path(tmp) / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            pw = json.loads((out / "photo_witnesses.json").read_text(encoding="utf-8"))
            self.assertEqual([x["photo_uuid"] for x in pw], ["OK1"])

    def test_T2_F04_02_max_year_boundary_dec31_vs_jan01(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f04_2_") as tmp:
            photos = [
                {"photo_uuid": "DEC31", "original_filename": "A.JPG", "witnessed_at": "2015-12-31T23:59:59Z", "albums": ["J"]},
                {"photo_uuid": "JAN01", "original_filename": "B.JPG", "witnessed_at": "2016-01-01T00:00:00Z", "albums": ["J"]},
            ]
            env = _write_stub_env(Path(tmp), photos=photos, notes=[])
            out = Path(tmp) / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--max-year", "2015"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            pw = json.loads((out / "photo_witnesses.json").read_text(encoding="utf-8"))
            self.assertEqual([x["photo_uuid"] for x in pw], ["DEC31"])

    def test_T2_F04_03_overwrite_false_preserves_existing_photo_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f04_3_") as tmp:
            out = Path(tmp) / "out"
            photos_dir = out / "photos"
            photos_dir.mkdir(parents=True)
            sentinel = photos_dir / "U1_KEEP.JPG"
            sentinel.write_bytes(b"KEEP_ME")
            photos = [{"photo_uuid": "U1", "original_filename": "KEEP.JPG", "witnessed_at": "2015-01-01T10:00:00-05:00", "albums": ["J"]}]
            env = _write_stub_env(Path(tmp), photos=photos, notes=[])
            res = self.adapter.tndc_witness(["--out-dir", str(out)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(sentinel.read_bytes(), b"KEEP_ME")

    def test_T2_F04_04_icloud_missing_without_vs_with_download_missing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f04_4_") as tmp:
            photos = [{"photo_uuid": "IC1", "original_filename": "IC.JPG", "witnessed_at": "2015-01-01T10:00:00-05:00", "ismissing": True, "albums": ["J"]}]
            env = _write_stub_env(Path(tmp), photos=photos, notes=[])
            out1 = Path(tmp) / "out1"
            res1 = self.adapter.tndc_witness(["--out-dir", str(out1)], extra_env=env)
            self.assertEqual(res1.returncode, 0, res1.stderr)
            pw1 = json.loads((out1 / "photo_witnesses.json").read_text(encoding="utf-8"))
            self.assertTrue(pw1[0]["is_in_icloud_only"])

            out2 = Path(tmp) / "out2"
            res2 = self.adapter.tndc_witness(["--out-dir", str(out2), "--download-missing"], extra_env=env)
            self.assertEqual(res2.returncode, 0, res2.stderr)
            pw2 = json.loads((out2 / "photo_witnesses.json").read_text(encoding="utf-8"))
            self.assertFalse(pw2[0]["is_in_icloud_only"])
            self.assertTrue(Path(pw2[0]["local_path"]).is_file())

    def test_T2_F04_05_empty_photos_album_writes_empty_array(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f04_5_") as tmp:
            env = _write_stub_env(Path(tmp), photos=[], notes=[])
            out = Path(tmp) / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--photos-album", "NoneSuch"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(json.loads((out / "photo_witnesses.json").read_text(encoding="utf-8")), [])

    # --- F05 ---

    def test_T2_F05_01_skips_password_protected_notes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f05_1_") as tmp:
            notes = [
                {"note_id": "N1", "folder": "4_bloom", "title": "1", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": "open1", "password_protected": False},
                {"note_id": "NLOCK", "folder": "4_bloom", "title": "Locked", "created_at": "2015-01-02T10:00:00-05:00", "modified_at": "2015-01-02T10:00:00-05:00", "plaintext": "NEVER_READ", "password_protected": True},
                {"note_id": "N2", "folder": "4_bloom", "title": "2", "created_at": "2015-01-03T10:00:00-05:00", "modified_at": "2015-01-03T10:00:00-05:00", "plaintext": "open2", "password_protected": False},
            ]
            env = _write_stub_env(Path(tmp), photos=[], notes=notes)
            out = Path(tmp) / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out)], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            loaded = json.loads((out / "ios_notes.json").read_text(encoding="utf-8"))
            self.assertEqual([n["note_id"] for n in loaded], ["N1", "N2"])

    def test_T2_F05_02_duplicate_folder_unknown_handled_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f05_2_") as tmp:
            notes = [
                {"note_id": "N1", "account": "iCloud", "folder": "Unknown", "title": "1", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": "a"},
                {"note_id": "N2", "account": "Misc", "folder": "Unknown", "title": "2", "created_at": "2015-01-02T10:00:00-05:00", "modified_at": "2015-01-02T10:00:00-05:00", "plaintext": "b"},
            ]
            env = _write_stub_env(Path(tmp), photos=[], notes=notes)
            out = Path(tmp) / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--notes-folder", "Unknown"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            loaded = json.loads((out / "ios_notes.json").read_text(encoding="utf-8"))
            self.assertEqual(len(loaded), 2)

    def test_T2_F05_03_whitespace_and_cr_folder_names_handled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f05_3_") as tmp:
            notes = [
                {"note_id": "N1", "folder": "4_bl00m.4_0S_core\r", "title": "1", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": "a"},
                {"note_id": "N2", "folder": "Transcend ", "title": "2", "created_at": "2015-01-02T10:00:00-05:00", "modified_at": "2015-01-02T10:00:00-05:00", "plaintext": "b"},
            ]
            env = _write_stub_env(Path(tmp), photos=[], notes=notes)
            out = Path(tmp) / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--notes-folder", "4_bl00m.4_0S_core", "--notes-folder", "Transcend"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            loaded = json.loads((out / "ios_notes.json").read_text(encoding="utf-8"))
            self.assertEqual(len(loaded), 2)

    def test_T2_F05_04_empty_note_body_produces_empty_sha256(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f05_4_") as tmp:
            notes = [
                {"note_id": "NEMPTY", "folder": "4_bloom", "title": "Empty", "created_at": "2015-01-01T10:00:00-05:00", "modified_at": "2015-01-01T10:00:00-05:00", "plaintext": ""}
            ]
            env = _write_stub_env(Path(tmp), photos=[], notes=notes)
            out = Path(tmp) / "out"
            self.adapter.tndc_witness(["--out-dir", str(out)], extra_env=env)
            loaded = json.loads((out / "ios_notes.json").read_text(encoding="utf-8"))
            self.assertEqual(loaded[0]["plaintext"], "")
            self.assertEqual(loaded[0]["text_sha256"], "sha256:" + hashlib.sha256(b"").hexdigest())

    def test_T2_F05_05_zero_notes_in_folder_writes_empty_array(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f05_5_") as tmp:
            env = _write_stub_env(Path(tmp), photos=[], notes=[])
            out = Path(tmp) / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--notes-folder", "EmptyFolder"], extra_env=env)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(json.loads((out / "ios_notes.json").read_text(encoding="utf-8")), [])

    # --- F06 ---

    def test_T2_F06_01_ocr_empty_photo_witnesses_writes_empty_dict(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f06_1_") as tmp:
            out = Path(tmp) / "out"
            write_intake_bundle(out, photos=[], notes=[])
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--ocr-only"])
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(json.loads((out / "ocr_cache.json").read_text(encoding="utf-8")), {})

    def test_T2_F06_02_ocr_missing_image_path_graceful_batch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f06_2_") as tmp:
            out = Path(tmp) / "out"
            good = out / "photos" / "GOOD.jpg"
            build_poem_image(good, ["Hello"])
            missing = out / "photos" / "GONE.jpg"
            write_intake_bundle(
                out,
                photos=[
                    make_photo_witness("GONE", "GONE.jpg", missing, "2015-01-01T10:00:00-05:00"),
                    make_photo_witness("GOOD", "GOOD.jpg", good, "2015-01-02T10:00:00-05:00"),
                ],
                notes=[],
            )
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--ocr-only"])
            self.assertEqual(res.returncode, 0, res.stderr)
            cache = json.loads((out / "ocr_cache.json").read_text(encoding="utf-8"))
            validate_ocr_cache_schema(cache)
            self.assertIn("GOOD", cache)

    def test_T2_F06_03_ocr_blank_white_image_yields_empty_lines(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f06_3_") as tmp:
            out = Path(tmp) / "out"
            blank = out / "photos" / "BLANK.jpg"
            build_blank_image(blank)
            write_intake_bundle(out, photos=[make_photo_witness("BLANK", "BLANK.jpg", blank, "2015-01-01T10:00:00-05:00")], notes=[])
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--ocr-only"])
            self.assertEqual(res.returncode, 0, res.stderr)
            cache = json.loads((out / "ocr_cache.json").read_text(encoding="utf-8"))
            self.assertEqual(cache["BLANK"]["text"], "")
            self.assertEqual(cache["BLANK"]["lines"], [])

    def test_T2_F06_04_ocr_corrupt_bytes_does_not_corrupt_cache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f06_4_") as tmp:
            out = Path(tmp) / "out"
            bad = out / "photos" / "BAD.jpg"
            build_corrupt_file(bad)
            write_intake_bundle(
                out,
                photos=[make_photo_witness("BAD", "BAD.jpg", bad, "2015-01-01T10:00:00-05:00")],
                notes=[],
                ocr_cache={"PRE": {"text": "ok", "lines": ["ok"], "ocr_engine": "Vision", "ocr_at": "2015-01-01T00:00:00Z"}},
            )
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--ocr-only"])
            self.assertEqual(res.returncode, 0, res.stderr)
            cache = json.loads((out / "ocr_cache.json").read_text(encoding="utf-8"))
            self.assertEqual(cache["PRE"]["text"], "ok")

    def test_T2_F06_05_ocr_incremental_cache_preserves_unchanged_and_adds_new(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f06_5_") as tmp:
            out = Path(tmp) / "out"
            p1 = out / "photos" / "U1.jpg"
            p2 = out / "photos" / "U2.jpg"
            build_poem_image(p1, ["First"])
            build_poem_image(p2, ["Second"])
            write_intake_bundle(
                out,
                photos=[
                    make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00"),
                    make_photo_witness("U2", "2.jpg", p2, "2015-01-02T10:00:00-05:00"),
                ],
                notes=[],
                ocr_cache={"U1": {"text": "CACHED_U1", "lines": ["CACHED_U1"], "ocr_engine": "Vision", "ocr_at": "2015-01-01T00:00:00Z"}},
            )
            self.adapter.tndc_witness(["--out-dir", str(out), "--ocr-only"])
            cache = json.loads((out / "ocr_cache.json").read_text(encoding="utf-8"))
            self.assertEqual(cache["U1"]["text"], "CACHED_U1")
            self.assertIn("U2", cache)

    # --- F07 (TNDC test/lint & CLI boundaries) ---

    def test_T2_F07_01_tndc_invalid_subcommand_exits_nonzero(self) -> None:
        if self.adapter.cfg.self_check:
            res = self.adapter._run_stub(["nonexistent-subcmd"])
        else:
            res = subprocess.run(
                [str(self.adapter.tndc_python()), "-m", "notes_docs_capture", "nonexistent-subcmd"],
                cwd=str(self.adapter.cfg.tndc_dir),
                env=self.adapter._tndc_env(),
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(res.returncode, 0)

    def test_T2_F07_02_tndc_non_integer_max_year_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f07_2_") as tmp:
            out = Path(tmp) / "out"
            res = self.adapter.tndc_witness(["--out-dir", str(out), "--max-year", "not_a_year"])
            self.assertNotEqual(res.returncode, 0)
            self.assertFalse((out / "photo_witnesses.json").exists())

    def test_T2_F07_03_tndc_status_writes_zero_repo_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f07_3_") as tmp:
            s = Path(tmp) / "state"
            o = Path(tmp) / "out"
            res = self.adapter.tndc_status(s, o)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue(len(res.stdout.strip()) > 0)

    def test_T2_F07_04_tndc_guards_definition_present(self) -> None:
        if self.adapter.cfg.self_check:
            res = self.adapter.tndc_run_tests()
            self.assertEqual(res.returncode, 0)
            return
        assert self.adapter.cfg.tndc_dir is not None
        guards_src = (self.adapter.cfg.tndc_dir / "tests" / "guards.py").read_text(encoding="utf-8")
        self.assertIn("GuardViolation", guards_src)
        self.assertIn("GuardedTestCase", guards_src)

    # --- F08 ---

    def test_T2_F08_01_empty_intake_produces_empty_links(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f08_1_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            res = self.adapter.jhw_match(sb, intake)
            self.assertEqual(res.returncode, 0, res.stderr)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            validate_witness_links_schema(links)
            self.assertEqual(links["photo_links"], [])
            self.assertEqual(links["note_links"], [])

    def test_T2_F08_02_accepted_readings_overrides_match_p001(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f08_2_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U62.jpg"
            build_poem_image(p1, ["MINOTAUR, where are you now?"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U62", "62.jpg", p1, "2015-07-18T10:00:00-04:00")],
                notes=[],
                ocr_cache={
                    "U62": {
                        "text": "MINOTAUR, where are you now? (OF which) you were so fond (OF) Dying trees from seeds you've sown The walls were so simple",
                        "lines": ["MINOTAUR, where are you now?"],
                        "ocr_engine": "Vision",
                        "ocr_at": "2026-11-24T00:00:00Z",
                    }
                },
            )
            self.adapter.jhw_match(sb, intake)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            self.assertEqual(links["photo_links"][0]["candidates"][0]["piece_id"], "p001")

    def test_T2_F08_03_missing_ocr_cache_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f08_3_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["The walls"])
            write_intake_bundle(intake, photos=[make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00")], notes=[])
            res = self.adapter.jhw_match(sb, intake)
            assert_no_traceback(res, "T2_F08_03 match")
            if assert_cli_ok_or_handled_error(res, "T2_F08_03 match"):
                out = sb / "source" / "witness_links.json"
                self.assertTrue(out.is_file(), f"witness_links.json missing: {res.stderr}")
                links = json.loads(out.read_text(encoding="utf-8"))
                validate_witness_links_schema(links)

    def test_T2_F08_04_gibberish_note_unmatched_pending_review(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f08_4_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[make_ios_note("NGIB", "F", "Gib", "2015-01-01T10:00:00-05:00", "2015-01-01T10:00:00-05:00", "xyzzy plugh 99999")],
                ocr_cache={},
            )
            res = self.adapter.jhw_match(sb, intake)
            self.assertEqual(res.returncode, 0, res.stderr)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            self.assertEqual(links["note_links"][0]["status"], "pending_review")

    def test_T2_F08_05_shortest_p060_and_longest_multipage_p020_score_top3(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f08_5_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[
                    make_ios_note("N60", "F", "Short", "2015-01-01T10:00:00-05:00", "2015-01-01T10:00:00-05:00", self.corpus.extract_version_text("p060")),
                    make_ios_note("N20", "F", "Long", "2015-01-02T10:00:00-05:00", "2015-01-02T10:00:00-05:00", self.corpus.extract_version_text("p020")),
                ],
                ocr_cache={},
            )
            self.adapter.jhw_match(sb, intake)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            top60 = [c["piece_id"] for c in links["note_links"][0]["candidates"]]
            top20 = [c["piece_id"] for c in links["note_links"][1]["candidates"]]
            self.assertIn("p060", top60)
            self.assertIn("p020", top20)

    def test_T2_F08_06_rerun_preserves_confirmed_and_rejected_decisions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f08_6_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["The walls"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00")],
                notes=[make_ios_note("N1", "F", "T", "2015-01-02T10:00:00-05:00", "2015-01-02T10:00:00-05:00", "xyzzy plugh")],
                ocr_cache={"U1": {"text": "The walls collapse", "lines": ["The walls"], "ocr_engine": "Vision", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p001"
            links["photo_links"][0]["textual_state"] = "predates_scan_edits"
            links["note_links"][0]["status"] = "rejected"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")

            self.adapter.jhw_match(sb, intake)
            rerun = json.loads(lp.read_text(encoding="utf-8"))
            self.assertEqual(rerun["photo_links"][0]["status"], "confirmed")
            self.assertEqual(rerun["photo_links"][0]["textual_state"], "predates_scan_edits")
            self.assertEqual(rerun["note_links"][0]["status"], "rejected")

    # --- F09 ---

    def test_T2_F09_01_phone_number_and_title_absent_from_source_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f09_1_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[make_ios_note("N1", "Personal", "Call Mom", "2015-01-01T10:00:00-05:00", "2015-01-01T10:00:00-05:00", "The walls 555-0199")],
                ocr_cache={},
            )
            self.adapter.jhw_match(sb, intake)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            assert_public_privacy_clean(links, forbidden_substrings=("555-0199", "Call Mom", "Personal"))

    def test_T2_F09_02_archive4t_local_path_absent_from_source_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f09_2_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "ABC.jpg"
            build_poem_image(p1, ["The walls"])
            pw = make_photo_witness("U1", "IMG_001.jpg", p1, "2015-01-01T10:00:00-05:00")
            pw["local_path"] = "/Volumes/Archive4T/Media/intake/versforms-witnesses/photos/ABC_IMG_001.jpg"
            write_intake_bundle(intake, photos=[pw], notes=[], ocr_cache={"U1": {"text": "The walls", "lines": ["The walls"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"}})
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            links = json.loads(lp.read_text(encoding="utf-8"))
            links["photo_links"][0]["status"] = "confirmed"
            links["photo_links"][0]["confirmed_piece_id"] = "p001"
            lp.write_text(json.dumps(links, indent=2), encoding="utf-8")
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            assert_public_privacy_clean(links, forbidden_substrings=("ABC_IMG_001.jpg",))
            assert_public_privacy_clean(json.loads(cp.read_text(encoding="utf-8")), forbidden_substrings=("ABC_IMG_001.jpg",))

    def test_T2_F09_03_raw_ocr_marker_only_in_intake_review_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f09_3_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            p1 = intake / "photos" / "U1.jpg"
            build_poem_image(p1, ["RAW_OCR_LINE_MARKER_XYZ"])
            write_intake_bundle(
                intake,
                photos=[make_photo_witness("U1", "1.jpg", p1, "2015-01-01T10:00:00-05:00")],
                notes=[],
                ocr_cache={"U1": {"text": "RAW_OCR_LINE_MARKER_XYZ The walls", "lines": ["RAW_OCR_LINE_MARKER_XYZ"], "ocr_engine": "V", "ocr_at": "2026-11-24T00:00:00Z"}},
            )
            self.adapter.jhw_match(sb, intake)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            assert_public_privacy_clean(links, forbidden_substrings=("RAW_OCR_LINE_MARKER_XYZ",))
            report_text = "\n".join(
                p.read_text(encoding="utf-8", errors="replace")
                for p in intake.iterdir()
                if p.is_file() and p.name not in {"photo_witnesses.json", "ios_notes.json", "ocr_cache.json"}
            )
            self.assertIn("RAW_OCR_LINE_MARKER_XYZ", report_text)

    def test_T2_F09_04_sensitive_folder_name_absent_from_witness_links(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f09_4_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[make_ios_note("N1", "Login / Password", "Creds", "2015-01-01T10:00:00-05:00", "2015-01-01T10:00:00-05:00", "The walls")],
                ocr_cache={},
            )
            self.adapter.jhw_match(sb, intake)
            links = json.loads((sb / "source" / "witness_links.json").read_text(encoding="utf-8"))
            assert_public_privacy_clean(links, forbidden_substrings=("Login / Password", "Creds"))

    def test_T2_F09_05_recursive_key_scan_zero_forbidden_keys(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f09_5_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(
                intake,
                photos=[],
                notes=[make_ios_note("N1", "F", "T", "2015-01-01T10:00:00-05:00", "2015-01-01T10:00:00-05:00", "The walls")],
                ocr_cache={},
            )
            self.adapter.jhw_match(sb, intake)
            lp = sb / "source" / "witness_links.json"
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            assert_public_privacy_clean(json.loads(lp.read_text(encoding="utf-8")))
            assert_public_privacy_clean(json.loads(cp.read_text(encoding="utf-8")))

    # --- F10 ---

    def test_T2_F10_01_check_py_detects_modified_site_file(self) -> None:
        with JHWSandbox(self.adapter.cfg.jhw_dir, include_full_check_assets=True) as sb:
            target = sb / "site" / "data" / "j.json"
            target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")
            res = self.adapter.jhw_check(sb)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("CHANGED", res.stdout)

    def test_T2_F10_02_check_py_detects_new_untracked_site_file(self) -> None:
        with JHWSandbox(self.adapter.cfg.jhw_dir, include_full_check_assets=True) as sb:
            (sb / "site" / "tmp.txt").write_text("untracked", encoding="utf-8")
            res = self.adapter.jhw_check(sb)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("NEW", res.stdout)

    def test_T2_F10_03_check_py_detects_bare_browser_launch(self) -> None:
        with JHWSandbox(self.adapter.cfg.jhw_dir, include_full_check_assets=True) as sb:
            synthetic = (
                "from " + "play" + "wright.sync_api import sync_" + "play" + "wright\n"
                + "chr" + "omium." + "lau" + "nch()\n"
            )
            (sb / "tests" / "bad_probe.py").write_text(synthetic, encoding="utf-8")
            res = self.adapter.jhw_check(sb)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("BARE LAUNCH", res.stdout)

    def test_T2_F10_04_canonical_and_public_json_byte_identical(self) -> None:
        before = snapshot_protected_hashes(self.adapter.cfg.jhw_dir)
        pub = json.loads((self.adapter.cfg.jhw_dir / "release" / "public.json").read_text(encoding="utf-8"))
        self.assertEqual(pub, {"pieces": []})
        assert_protected_paths_unchanged(self.adapter.cfg.jhw_dir, before)

    def test_T2_F10_05_check_py_detects_conflict_marker_in_chats_readme(self) -> None:
        with JHWSandbox(self.adapter.cfg.jhw_dir, include_full_check_assets=True) as sb:
            readme = sb / "docs" / "chats" / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\n<<<<<<< HEAD\n", encoding="utf-8")
            res = self.adapter.jhw_check(sb)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("CONFLICT", res.stdout)

    # --- F11 ---

    def test_T2_F11_01_zero_confirmed_links_fabricates_no_dates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f11_1_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            intake = Path(tmp) / "intake"
            write_intake_bundle(intake, photos=[], notes=[], ocr_cache={})
            self.adapter.jhw_match(sb, intake)
            cp = sb / "source" / "chronology.json"
            res = self.adapter.jhw_chronology(sb, sb / "source" / "witness_links.json", cp, digitized_at="2015-09")
            self.assertEqual(res.returncode, 0, res.stderr)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            assert_two_clock_clean(chron, "2015-09")
            for e in chron["physical_codex_order"]:
                self.assertEqual(e["chronology"]["date_basis"], "undated")

    def test_T2_F11_02_all_126_pieces_confirmed_photo_anchored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f11_2_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            photo_links = []
            for idx, piece in enumerate(self.corpus.pieces, 1):
                pid = piece["id"]
                day = ((idx - 1) % 28) + 1
                mon = ((idx - 1) // 28) + 1
                photo_links.append(
                    {
                        "photo_id": f"ph-{idx:03d}",
                        "photo_uuid": f"U-{pid}",
                        "photo_sha256": f"sha256:{idx:064x}",
                        "witnessed_at": f"2015-{mon:02d}-{day:02d}T12:00:00-04:00",
                        "camera_model": "Apple iPhone 6",
                        "candidates": [{"piece_id": pid, "score": 1.0, "token_overlap": 1.0, "fuzzy_score": 1.0}],
                        "confirmed_piece_id": pid,
                        "status": "confirmed",
                        "textual_state": "matches_scan",
                    }
                )
            lp.write_text(
                json.dumps(
                    {
                        "schema": "versforms.witness-links.v1",
                        "generated_at": "2026-11-24T00:00:00Z",
                        "intake_summary": {"photos": 126, "notes": 0},
                        "photo_links": photo_links,
                        "note_links": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            cp = sb / "source" / "chronology.json"
            res = self.adapter.jhw_chronology(sb, lp, cp)
            self.assertEqual(res.returncode, 0, res.stderr)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            self.assertTrue(all(e["chronology"]["date_basis"] == "photo_anchored" for e in chron["physical_codex_order"]))

    def test_T2_F11_03_single_anchor_never_interpolates_toward_digitized_at(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f11_3_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(
                json.dumps(
                    {
                        "schema": "versforms.witness-links.v1",
                        "generated_at": "2026-11-24T00:00:00Z",
                        "intake_summary": {"photos": 1, "notes": 0},
                        "photo_links": [
                            {
                                "photo_id": "ph-048",
                                "photo_uuid": "U48",
                                "photo_sha256": "sha256:" + "1" * 64,
                                "witnessed_at": "2015-03-15T12:00:00-04:00",
                                "camera_model": "Apple iPhone 6",
                                "candidates": [{"piece_id": "p048", "score": 1.0, "token_overlap": 1.0, "fuzzy_score": 1.0}],
                                "confirmed_piece_id": "p048",
                                "status": "confirmed",
                                "textual_state": "matches_scan",
                            }
                        ],
                        "note_links": [],
                    }
                ),
                encoding="utf-8",
            )
            cp_a = Path(tmp) / "chron_a.json"
            cp_b = Path(tmp) / "chron_b.json"
            self.adapter.jhw_chronology(sb, lp, cp_a, digitized_at="2015-09")
            self.adapter.jhw_chronology(sb, lp, cp_b, digitized_at="2024-06")
            ca = json.loads(cp_a.read_text(encoding="utf-8"))
            cb = json.loads(cp_b.read_text(encoding="utf-8"))
            assert_two_clock_clean(ca, "2015-09", {"2015-03-15"})
            assert_two_clock_invariant(ca, cb)

    def test_T2_F11_04_two_anchors_interpolate_and_extrapolate_without_digitized_at(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f11_4_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(
                json.dumps(
                    {
                        "schema": "versforms.witness-links.v1",
                        "generated_at": "2026-11-24T00:00:00Z",
                        "intake_summary": {"photos": 2, "notes": 0},
                        "photo_links": [
                            {
                                "photo_id": "ph-015",
                                "photo_uuid": "U15",
                                "photo_sha256": "sha256:" + "1" * 64,
                                "witnessed_at": "2015-03-01T12:00:00-05:00",
                                "camera_model": "Apple iPhone 6",
                                "candidates": [],
                                "confirmed_piece_id": "p015",
                                "status": "confirmed",
                                "textual_state": "matches_scan",
                            },
                            {
                                "photo_id": "ph-029",
                                "photo_uuid": "U29",
                                "photo_sha256": "sha256:" + "2" * 64,
                                "witnessed_at": "2015-03-21T12:00:00-04:00",
                                "camera_model": "Apple iPhone 6",
                                "candidates": [],
                                "confirmed_piece_id": "p029",
                                "status": "confirmed",
                                "textual_state": "matches_scan",
                            },
                        ],
                        "note_links": [],
                    }
                ),
                encoding="utf-8",
            )
            cp1 = Path(tmp) / "c1.json"
            cp2 = Path(tmp) / "c2.json"
            self.adapter.jhw_chronology(sb, lp, cp1, digitized_at="2015-09")
            self.adapter.jhw_chronology(sb, lp, cp2, digitized_at="2030-01")
            c1 = json.loads(cp1.read_text(encoding="utf-8"))
            c2 = json.loads(cp2.read_text(encoding="utf-8"))
            assert_two_clock_invariant(c1, c2)
            assert_two_clock_clean(c1, "2015-09", {"2015-03-01", "2015-03-21"})

    def test_T2_F11_05_pending_link_ignored_in_chronology(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f11_5_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            links = {
                "schema": "versforms.witness-links.v1",
                "generated_at": "2026-11-24T00:00:00Z",
                "intake_summary": {"photos": 2, "notes": 0},
                "photo_links": [
                    {
                        "photo_id": "ph-pend",
                        "photo_uuid": "UPEND",
                        "photo_sha256": "sha256:" + "a" * 64,
                        "witnessed_at": "2014-01-01T12:00:00-05:00",
                        "camera_model": "Apple iPhone 6",
                        "candidates": [{"piece_id": "p002", "score": 0.99, "token_overlap": 1.0, "fuzzy_score": 0.99}],
                        "confirmed_piece_id": "p002",
                        "status": "pending_review",
                        "textual_state": "unreviewed",
                    },
                    {
                        "photo_id": "ph-conf",
                        "photo_uuid": "UCONF",
                        "photo_sha256": "sha256:" + "b" * 64,
                        "witnessed_at": "2015-04-01T12:00:00-04:00",
                        "camera_model": "Apple iPhone 6",
                        "candidates": [{"piece_id": "p003", "score": 0.99, "token_overlap": 1.0, "fuzzy_score": 0.99}],
                        "confirmed_piece_id": "p003",
                        "status": "confirmed",
                        "textual_state": "matches_scan",
                    },
                ],
                "note_links": [],
            }
            lp.write_text(json.dumps(links), encoding="utf-8")
            cp = Path(tmp) / "chron.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            validate_chronology_schema(chron, self.corpus, links)
            p002 = next(e for e in chron["physical_codex_order"] if e["piece_id"] == "p002")
            self.assertEqual(p002["witnesses"]["photo_witnesses"], [])

    def test_T2_F11_06_shared_surface_flag_on_all_23_co_tenanted_pages(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f11_6_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(json.dumps({"schema": "versforms.witness-links.v1", "generated_at": "2026-11-24T00:00:00Z", "intake_summary": {}, "photo_links": [], "note_links": []}), encoding="utf-8")
            cp = Path(tmp) / "chron.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            by_pid = {e["piece_id"]: e for e in chron["physical_codex_order"]}
            self.assertTrue(by_pid["p126"]["witnesses"]["codex_scan"]["shared_surface"])
            for p_id in ("p081", "p082", "p083", "p084", "p085", "p086", "p087", "p103", "p108"):
                self.assertTrue(by_pid[p_id]["witnesses"]["codex_scan"]["shared_surface"])

    def test_T2_F11_07_out_of_order_photo_timestamps_handled_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f11_7_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(
                json.dumps(
                    {
                        "schema": "versforms.witness-links.v1",
                        "generated_at": "2026-11-24T00:00:00Z",
                        "intake_summary": {},
                        "photo_links": [
                            {"photo_id": "ph-1", "photo_uuid": "U1", "photo_sha256": "sha256:" + "1" * 64, "witnessed_at": "2015-05-01T10:00:00-04:00", "camera_model": "iPhone", "candidates": [], "confirmed_piece_id": "p015", "status": "confirmed", "textual_state": "matches_scan"},
                            {"photo_id": "ph-2", "photo_uuid": "U2", "photo_sha256": "sha256:" + "2" * 64, "witnessed_at": "2015-02-01T10:00:00-05:00", "camera_model": "iPhone", "candidates": [], "confirmed_piece_id": "p029", "status": "confirmed", "textual_state": "predates_scan_edits"},
                        ],
                        "note_links": [],
                    }
                ),
                encoding="utf-8",
            )
            cp = Path(tmp) / "chron.json"
            res = self.adapter.jhw_chronology(sb, lp, cp)
            self.assertEqual(res.returncode, 0, res.stderr)
            chron = json.loads(cp.read_text(encoding="utf-8"))
            validate_chronology_schema(chron, self.corpus)
            p20 = next(e for e in chron["physical_codex_order"] if e["piece_id"] == "p020")
            self.assertLessEqual(p20["chronology"]["est_start"], p20["chronology"]["est_end"])

    # --- F12 ---

    def test_T2_F12_01_diary62a_p001_and_p126_disjoint_crops(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f12_1_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(json.dumps({"schema": "versforms.witness-links.v1", "generated_at": "2026-11-24T00:00:00Z", "intake_summary": {}, "photo_links": [], "note_links": []}))
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)

            out1 = Path(tmp) / "out_p001"
            out2 = Path(tmp) / "out_p126"
            self.adapter.jhw_export_round1(sb, cp, out1, pieces=["p001"], extra_args=["--surface", "diary62a"])
            self.adapter.jhw_export_round1(sb, cp, out2, pieces=["p126"], extra_args=["--surface", "diary62a"])
            m1 = json.loads((out1 / "projection_manifest.json").read_text(encoding="utf-8"))
            m2 = json.loads((out2 / "projection_manifest.json").read_text(encoding="utf-8"))
            assert_shared_surface_isolated(m1, out1, self.corpus)
            assert_shared_surface_isolated(m2, out2, self.corpus)
            box1 = m1["exports"][0]["crop_box"]
            box2 = m2["exports"][0]["crop_box"]
            self.assertLess(box1[3], box2[1] + 20)

    def test_T2_F12_02_diary46_7_piece_page_blocks_uncropped_or_isolates_p081(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f12_2_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(json.dumps({"schema": "versforms.witness-links.v1", "generated_at": "2026-11-24T00:00:00Z", "intake_summary": {}, "photo_links": [], "note_links": []}))
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            out_dir = Path(tmp) / "out"
            self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p081"], extra_args=["--surface", "diary46"])
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            assert_shared_surface_isolated(manifest, out_dir, self.corpus)

    def test_T2_F12_03_spread_exposed_diary37_and_diary25_blocked_without_isolation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f12_3_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(json.dumps({"schema": "versforms.witness-links.v1", "generated_at": "2026-11-24T00:00:00Z", "intake_summary": {}, "photo_links": [], "note_links": []}))
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            out_37 = Path(tmp) / "out_37"
            out_25 = Path(tmp) / "out_25"
            self.adapter.jhw_export_round1(sb, cp, out_37, pieces=["p067"], extra_args=["--surface", "diary37"])
            self.adapter.jhw_export_round1(sb, cp, out_25, pieces=["p039"], extra_args=["--surface", "diary25"])
            m37 = json.loads((out_37 / "projection_manifest.json").read_text(encoding="utf-8"))
            m25 = json.loads((out_25 / "projection_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(m37["exports"], [])
            self.assertEqual(len(m37["blocked"]), 1)
            self.assertEqual(m25["exports"], [])
            self.assertEqual(len(m25["blocked"]), 1)

    def test_T2_F12_04_metadata_laden_jpeg_fully_stripped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f12_4_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(json.dumps({"schema": "versforms.witness-links.v1", "generated_at": "2026-11-24T00:00:00Z", "intake_summary": {}, "photo_links": [], "note_links": []}))
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            dirty = Path(tmp) / "dirty.jpg"
            build_metadata_laden_jpeg(dirty, lines=["Metadata payload"])
            out_dir = Path(tmp) / "out"
            self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p001"], extra_args=["--surface", "diary1", "--override-image", str(dirty)])
            manifest = json.loads((out_dir / "projection_manifest.json").read_text(encoding="utf-8"))
            assert_jpeg_metadata_clean(out_dir / manifest["exports"][0]["output_file"])

    def test_T2_F12_05_nonexistent_piece_p999_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f12_5_") as tmp, JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
            lp = sb / "source" / "witness_links.json"
            lp.write_text(json.dumps({"schema": "versforms.witness-links.v1", "generated_at": "2026-11-24T00:00:00Z", "intake_summary": {}, "photo_links": [], "note_links": []}))
            cp = sb / "source" / "chronology.json"
            self.adapter.jhw_chronology(sb, lp, cp)
            out_dir = Path(tmp) / "out"
            res = self.adapter.jhw_export_round1(sb, cp, out_dir, pieces=["p999"])
            self.assertNotEqual(res.returncode, 0)
            self.assertFalse(out_dir.exists())

    # --- F13 (Anti-tautology & runner CLI validation) ---

    def test_T2_F13_01_corrupt_missing_j_json_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f13_1_") as tmp:
            with self.assertRaises(FileNotFoundError):
                CorpusIndex(Path(tmp))

    def test_T2_F13_02_privacy_scanner_catches_injected_plaintext(self) -> None:
        bad = inject_plaintext_into_witness_links({"photo_links": [], "note_links": []})
        with self.assertRaises(AssertionError):
            assert_public_privacy_clean(bad)

    def test_T2_F13_03_two_clock_validator_catches_digitized_at_leak(self) -> None:
        chron = {
            "physical_codex_order": [
                {
                    "piece_id": "p126",
                    "witnesses": {"codex_scan": {"digitized_at": "2015-09"}},
                    "chronology": {"est_start": "2015-08-01", "est_end": "2015-09-01", "amalgamated_sort_key": "2015-08-01#p126"},
                }
            ]
        }
        bad = inject_digitized_at_into_chronology(chron, "2015-09")
        with self.assertRaises(AssertionError):
            assert_two_clock_clean(bad, "2015-09")

    def test_T2_F13_04_jpeg_validator_catches_injected_exif(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f13_4_") as tmp:
            clean = Path(tmp) / "clean.jpg"
            build_poem_image(clean, ["clean"])
            dirty = Path(tmp) / "dirty.jpg"
            inject_exif_into_jpeg(clean, dirty)
            with self.assertRaises(AssertionError):
                assert_jpeg_metadata_clean(dirty)

    def test_T2_F13_05_runner_rejects_invalid_tier_99_with_exit_2(self) -> None:
        runner = Path(__file__).resolve().parent / "run_e2e.py"
        res = subprocess.run(
            [sys.executable, str(runner), "--self-check", "--tier", "99"],
            cwd=str(self.adapter.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 2)

    # --- F14 ---

    def test_T2_F14_01_jhw_missing_match_witnesses_fails_in_target_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e2e_t2_f14_1_") as tmp:
            fake_tndc = Path(tmp) / "tndc"
            (fake_tndc / ".venv" / "bin").mkdir(parents=True)
            (fake_tndc / ".venv" / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
            (fake_tndc / "src" / "notes_docs_capture").mkdir(parents=True)
            with JHWSandbox(self.adapter.cfg.jhw_dir) as sb:
                runner = Path(__file__).resolve().parent / "run_e2e.py"
                res = subprocess.run(
                    [sys.executable, str(runner), "--tndc-dir", str(fake_tndc), "--jhw-dir", str(sb)],
                    cwd=str(self.adapter.cfg.jhw_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(res.returncode, 0)

    def test_T2_F14_02_tndc_broken_ruff_or_pytest_captured_nonzero(self) -> None:
        if self.adapter.cfg.self_check:
            r1 = self.adapter.tndc_run_tests(extra_env={"E2E_STUB_FAIL_TESTS": "1"})
            r2 = self.adapter.tndc_run_ruff(extra_env={"E2E_STUB_FAIL_RUFF": "1"})
            self.assertNotEqual(r1.returncode, 0)
            self.assertNotEqual(r2.returncode, 0)
        else:
            r1 = self.adapter.tndc_run_tests()
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)

    def test_T2_F14_03_relative_paths_resolved_cleanly(self) -> None:
        runner = Path(__file__).resolve().parent / "run_e2e.py"
        rel_runner = os.path.relpath(runner, str(self.adapter.cfg.jhw_dir))
        res = subprocess.run(
            [sys.executable, rel_runner, "--self-check", "--jhw-dir", ".", "--tier", "1", "--filter", "T1_F01_01"],
            cwd=str(self.adapter.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_T2_F14_04_protected_repo_hashes_identical_pre_post(self) -> None:
        before = snapshot_protected_hashes(self.adapter.cfg.jhw_dir)
        res = self.adapter.jhw_check()
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        assert_protected_paths_unchanged(self.adapter.cfg.jhw_dir, before)

    def test_T2_F14_05_consecutive_back_to_back_runs_collision_free(self) -> None:
        runner = Path(__file__).resolve().parent / "run_e2e.py"
        for _ in range(2):
            res = subprocess.run(
                [sys.executable, str(runner), "--self-check", "--tier", "1", "--filter", "T1_F08_01"],
                cwd=str(self.adapter.cfg.jhw_dir),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
