#!/usr/bin/env python3
"""Tests for the T08 shared source-region contract and eligibility engine.

    python3 -m unittest tests.test_source_regions -v

The tests use the committed pilot manifest, the derived (non-author) pilot
policy and synthetic fixtures. Nothing here is an author decision, and no
transcribed poem text is read or written.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import source_regions as sr  # noqa: E402

PILOT = ROOT / "docs/pilots/t08-p001/p001.source-regions.json"
COMBOS = ROOT / "docs/pilots/t08-p001/fixtures/synthetic-combinations.source-regions.json"
POLICY = ROOT / "docs/pilots/t08-p001/visibility-policy.json"
FIXTURES = ROOT / "docs/pilots/t08-p001/fixtures"
COMBO_PREFIX = "vf:atom:p001/p001-diary1-0/diary1/combination"

sys.path.insert(0, str(ROOT / "tests"))
import release_fixtures


def evaluate(manifest, policy, scope):
    context = release_fixtures.regions(manifest) if policy.get("status") == "synthetic-fixture-for-tests-not-a-decision" else None
    return sr.evaluate(manifest, policy, scope, release_context=context)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def reseal(manifest: dict) -> dict:
    out = copy.deepcopy(manifest)
    out.pop("integrity", None)
    out["integrity"] = {"content_sha256": sr.canonical_sha256(out)}
    return out


def atom(manifest: dict, suffix: str) -> dict:
    wanted = f"{COMBO_PREFIX}/{suffix}"
    return next(a for a in manifest["atoms"] if a["atom_id"] == wanted)


def cleared_policy(manifest: dict, *, pieces: dict | None = None,
                   whitelist: list[str] | None = None,
                   **overrides) -> dict:
    """A synthetic full-clearance policy: a positive control, not a decision."""
    pieces = pieces or {"p001": {"pool": "series", "withheld_versions": [],
                                 "excluded_versions": [], "strike_through_vetoes": [],
                                 "piece_vetoes": []}}
    policy = {
        "schema": sr.POLICY_SCHEMA,
        "policy_id": "synthetic-cleared-public-test-only",
        "status": "synthetic-fixture-for-tests-not-a-decision",
        "publication": {"enabled": False},
        "author_clearance": {
            "status": "cleared",
            "covers_manifest_sha256": sr.manifest_digest(manifest),
            "statement_ref": "synthetic-test-only",
        },
        "release_gate": {
            "contract": "versforms.release-clearance.v1",
            "status": "cleared",
            "may_publish": True,
            "may_schedule_external_actions": False,
            "input_manifest_sha256": "synthetic-test-only",
            "exposure_manifest_sha256": "synthetic-test-only",
            "filing_evidence_ref": "synthetic-test-only",
            "acceptance_receipt_ref": "synthetic-test-only",
            "rollback_record_ref": "synthetic-test-only",
        },
        "machine_misread": {"status": "cleared", "source": "synthetic test only"},
        "shared_scan_resolution": {"status": "none", "pages": {}},
        "public_whitelist": whitelist if whitelist is not None else ["p001"],
        "withheld_pages": [],
        "withheld_assets": [],
        "pieces": pieces,
    }
    policy.update(copy.deepcopy(overrides))
    return policy


class PilotManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load(PILOT)

    def test_pilot_verifies_and_counts(self):
        result = sr.verify_manifest(self.manifest)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(self.manifest["counts"], {
            "atoms": 441, "poems": 1, "stanzas": 6, "lines": 22,
            "words": 86, "glyphs": 306, "marks": 20, "uncertainties": 3,
        })

    def test_pilot_has_no_transcribed_text_fields(self):
        for path, value in sr._walk_keys(self.manifest):
            key = path.rsplit(".", 1)[-1]
            if key in sr.FORBIDDEN_TEXT_KEYS:
                self.assertIn(value, (None, ""), f"text at {path}")

    def test_pilot_records_uncertainty_and_withdrawn_crop_as_open_states(self):
        uncertainties = self.manifest["uncertainties"]
        self.assertEqual(len(uncertainties), 3)
        self.assertTrue(all(u["status"] == "open" for u in uncertainties))
        line13 = next(a for a in self.manifest["atoms"]
                      if a["source_ids"].get("line_id") == "diary1-3-2")
        self.assertEqual(line13["reading"]["review_state"],
                         "crop-withdrawn-by-owner-eye-review")
        self.assertIsNone(line13["reading"]["text_ref"])

    def test_pilot_keeps_missing_author_box_explicit(self):
        line1 = next(a for a in self.manifest["atoms"]
                     if a["source_ids"].get("line_id") == "diary1-2-3")
        self.assertEqual(line1["author_box"]["state"], "missing-in-site-data")

    def test_lineage_closes_through_poem_and_stanza(self):
        line = next(a for a in self.manifest["atoms"]
                    if a["source_ids"].get("line_id") == "diary1-0-1")
        closure = sr.lineage_closure(self.manifest, line["atom_id"])
        self.assertIn("diary1-0-1", closure["source_line_ids"])
        self.assertEqual(closure["root_source_asset_ids"], ["scan:p/diary1"])
        self.assertIn("method:seam-partition-v1", closure["methods"])
        self.assertIn("vf:atom:p001/p001-diary1-0/poem", closure["atoms"])

    def test_integrity_tamper_is_rejected(self):
        broken = copy.deepcopy(self.manifest)
        line = next(a for a in broken["atoms"] if a["unit"] == "line")
        line["region"]["bbox"][0] += 1
        result = sr.verify_manifest(broken)
        self.assertFalse(result["ok"])
        self.assertTrue(any("integrity" in e for e in result["errors"]))

    def test_text_injection_is_rejected(self):
        broken = copy.deepcopy(self.manifest)
        broken["atoms"][0]["reading"]["text"] = "synthetic"
        broken = reseal(broken)
        result = sr.verify_manifest(broken)
        self.assertFalse(result["ok"])
        self.assertTrue(any("transcribed text field" in e for e in result["errors"]))

    def test_undeclared_method_is_rejected(self):
        broken = copy.deepcopy(self.manifest)
        line = next(a for a in broken["atoms"] if a["unit"] == "line")
        line["lineage"]["method_id"] = "method:not-declared"
        broken = reseal(broken)
        result = sr.verify_manifest(broken)
        self.assertFalse(result["ok"])
        self.assertTrue(any("is not declared" in e for e in result["errors"]))

    def test_region_frame_must_be_source_pixels(self):
        broken = copy.deepcopy(self.manifest)
        broken["atoms"][0]["region"]["frame"] = "screen"
        broken = reseal(broken)
        result = sr.verify_manifest(broken)
        self.assertFalse(result["ok"])
        self.assertTrue(any("region.frame" in e for e in result["errors"]))

    def test_schemas_are_valid_json(self):
        for name in ("source-region-v1.schema.json", "visibility-policy-v1.schema.json"):
            schema = load(ROOT / "docs/schemas" / name)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIn("$defs", schema)

    def test_pilot_inventory_is_current(self):
        inventory = load(PILOT.parent / "pilot-manifest.json")
        listed = {f["path"]: f for f in inventory["files"]}
        actual = {
            p.relative_to(ROOT).as_posix(): p
            for p in PILOT.parent.rglob("*")
            if p.is_file() and p.name not in {"pilot-manifest.json", ".DS_Store"}
        }
        self.assertEqual(set(listed), set(actual), "run tools/t08_pilot_manifest.py")
        for rel, path in actual.items():
            self.assertEqual(listed[rel]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest(), rel)

    def test_build_is_reproducible_when_owner_artifact_is_available(self):
        recorded = self.manifest["derivations"][0]
        atoms = Path(os.environ.get(
            "T08_ATOMS",
            str(ROOT / "proto/alive/atoms-p001.json"),
        ))
        self.assertTrue(atoms.is_file(), f"recovered owner atoms artifact is missing: {atoms}")
        digest = hashlib.sha256(atoms.read_bytes()).hexdigest()
        self.assertEqual(digest, recorded["artifact_sha256"], "owner input differs from preserved pilot evidence")
        rebuilt = sr.build_manifest(atoms, atoms_ref=recorded["artifact_ref"],
                                    atoms_commit=recorded["artifact_commit"])
        expected = copy.deepcopy(self.manifest)
        # The recovered input reproduces every geometry/identity/asset byte.
        # Only newly generated ownership metadata now names the completed T02
        # contract. The preserved historical manifest is never rewritten.
        for asset in expected["source_assets"]:
            self.assertEqual(asset["owner"], "T02 source/build/deposit (identifier owner; no completed T02 agreement located)")
            asset["owner"] = "T02 canonical source contract: docs/contracts/canonical-source.md (2026-11-06)"
        expected = reseal(expected)
        self.assertEqual(rebuilt, expected)


class EligibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load(PILOT)
        cls.derived = load(POLICY)
        cls.combos = load(COMBOS)

    def test_private_local_is_allowed_by_the_derived_defaults(self):
        report = evaluate(self.manifest, self.derived, "private-local")
        self.assertTrue(report["allowed"], report["manifest_reasons"])
        self.assertEqual(report["summary"]["inherited_pool"], "unassigned")

    def test_public_release_is_refused_by_the_derived_defaults(self):
        report = evaluate(self.manifest, self.derived, "public-release")
        self.assertFalse(report["allowed"])
        self.assertIn("author-clearance:missing", report["manifest_reasons"])
        self.assertIn("pool:unassigned-is-not-series", report["atom_reasons"][self.manifest["atoms"][0]["atom_id"]])
        self.assertIn("public-whitelist:piece-not-listed",
                      report["atom_reasons"][self.manifest["atoms"][0]["atom_id"]])
        self.assertIn("Record the author's Series/Reserve/Archive decision", " ".join(report["required_actions"]))

    def test_cleared_public_policy_is_a_positive_control(self):
        report = evaluate(self.manifest, cleared_policy(self.manifest), "public-release")
        self.assertTrue(report["allowed"], report["manifest_reasons"])
        self.assertEqual(report["atom_reasons"], {})
        self.assertIn("reading:open-uncertainty-present", report["warnings"])

    def test_release_gate_must_be_cleared_for_public_output(self):
        policy = cleared_policy(self.manifest)
        policy["release_gate"]["status"] = "awaiting-author-and-evidence"
        policy["release_gate"]["may_publish"] = False
        report = evaluate(self.manifest, policy, "public-release")
        self.assertFalse(report["allowed"])
        self.assertIn("release-gate:not-cleared", report["manifest_reasons"])
        self.assertIn("Complete the T03 release record", " ".join(report["required_actions"]))

    def test_unknown_scope_is_refused(self):
        with self.assertRaises(ValueError):
            evaluate(self.manifest, self.derived, "publish-everywhere")

    def test_reserve_inherits_privately_but_never_publishes(self):
        policy = load(FIXTURES / "policy-reserve.json")
        private = evaluate(self.manifest, policy, "private-local")
        self.assertTrue(private["allowed"], private["manifest_reasons"])
        self.assertEqual(private["summary"]["inherited_pool"], "reserve")
        public = evaluate(self.manifest, policy, "public-release")
        self.assertFalse(public["allowed"])
        self.assertTrue(any(r.startswith("pool:reserve") for r in public["atom_reasons"][self.manifest["atoms"][0]["atom_id"]]))

    def test_withheld_asset_and_page_are_refused_even_privately(self):
        report = evaluate(self.manifest, load(FIXTURES / "policy-withheld-asset.json"),
                             "private-local")
        self.assertFalse(report["allowed"])
        self.assertIn("source-asset:withheld:scan:p/diary1", report["manifest_reasons"])
        self.assertIn("page:withheld:diary1", report["manifest_reasons"])

    def test_version_exclusion_is_scope_aware(self):
        report = evaluate(self.manifest, load(FIXTURES / "policy-version-excluded.json"),
                             "private-local")
        self.assertFalse(report["allowed"])
        self.assertTrue(all(any("version:excluded-for-private-local" in r for r in reasons)
                            for reasons in report["atom_reasons"].values()))

    def test_strike_through_veto_is_private_and_scope_aware(self):
        private_only = cleared_policy(self.manifest)
        private_only["pieces"]["p001"]["strike_through_vetoes"] = [{
            "veto_id": "synthetic-private-veto",
            "line_ids": ["diary1-0-0"],
            "scopes": ["private-local"],
            "source": "synthetic test only",
        }]
        private = evaluate(self.manifest, private_only, "private-local")
        self.assertFalse(private["allowed"])
        self.assertTrue(any("strike-through-veto:synthetic-private-veto" in r
                            for r in private["atom_reasons"].values()))
        public = evaluate(self.manifest, private_only, "public-release")
        self.assertTrue(public["allowed"], public["manifest_reasons"])

        public_only = cleared_policy(self.manifest)
        public_only["pieces"]["p001"]["strike_through_vetoes"] = [{
            "veto_id": "synthetic-public-veto",
            "line_ids": ["diary1-0-0"],
            "scopes": ["public-release"],
            "source": "synthetic test only",
        }]
        self.assertTrue(evaluate(self.manifest, public_only, "private-local")["allowed"])
        public = evaluate(self.manifest, public_only, "public-release")
        self.assertFalse(public["allowed"])
        self.assertTrue(any("strike-through-veto:synthetic-public-veto" in r
                            for r in public["atom_reasons"].values()))

    def test_shared_scan_needs_every_neighbour_cleared(self):
        neighbour = {
            "atom_id": "vf:atom:p126/p126-synthetic-0/poem",
            "unit": "poem",
            "piece_id": "p126",
            "version_id": "p126-synthetic-0",
            "page_id": "diary1",
            "parent_atom_id": None,
            "source_ids": {"piece_id": "p126", "version_id": "p126-synthetic-0"},
            "region": {"frame": "source-pixels", "bbox": [0, 0, 10, 10], "polygon": None,
                       "method_id": "method:union-box-v1"},
            "source_asset_ids": ["scan:p/diary1"],
            "lineage": {"parent_atom_id": None, "input_atom_ids": [],
                        "root_source_asset_ids": ["scan:p/diary1"], "source_line_ids": [],
                        "method_id": "method:union-box-v1", "derivation_ids": []},
            "reading": {"transcription_state": "synthetic-fixture", "review_state": "synthetic-fixture",
                        "uncertainty_ids": [], "deliberate_misread": None, "text_ref": None},
            "credit": {"origin_kind": "author", "source_atom_ids": [],
                       "credit_required": False, "credit_style": None},
        }
        shared = sr.add_combinations(self.manifest, [neighbour])
        self.assertTrue(sr.verify_manifest(shared)["ok"])
        pieces = {
            "p001": {"pool": "series", "withheld_versions": [], "excluded_versions": [],
                     "strike_through_vetoes": [], "piece_vetoes": []},
            "p126": {"pool": "reserve", "withheld_versions": [], "excluded_versions": [],
                     "strike_through_vetoes": [], "piece_vetoes": []},
        }
        report = evaluate(shared, cleared_policy(shared, pieces=pieces,
                                                    whitelist=["p001", "p126"]),
                             "public-release")
        self.assertFalse(report["allowed"])
        self.assertIn("shared-scan:unresolved-neighbour:diary1:p126", report["manifest_reasons"])

        pieces["p126"]["pool"] = "series"
        policy = cleared_policy(shared, pieces=pieces, whitelist=["p001", "p126"])
        policy["shared_scan_resolution"] = {"status": "cleared", "pages": {"diary1": {
            "resolution_id": "synthetic-page-resolution", "source": "synthetic test only"}}}
        resolved = evaluate(shared, policy, "public-release")
        self.assertTrue(resolved["allowed"], resolved["manifest_reasons"])

    def test_borrowed_line_needs_credit_style_for_public_output(self):
        borrowed = atom(self.combos, "borrowed-synthetic-1")["atom_id"]
        cut = atom(self.combos, "cut-synthetic-1")["atom_id"]
        cipher = atom(self.combos, "cipher-synthetic-1")["atom_id"]
        report = evaluate(self.combos, cleared_policy(self.combos), "public-release")
        self.assertFalse(report["allowed"])
        self.assertIn("borrowed-line:credit-style-unresolved", report["atom_reasons"][borrowed])
        self.assertNotIn(cut, report["atom_reasons"])
        self.assertNotIn(cipher, report["atom_reasons"])

        fixed = copy.deepcopy(self.combos)
        atom(fixed, "borrowed-synthetic-1")["credit"]["credit_style"] = "epigraph-with-source"
        fixed = reseal(fixed)
        allowed = evaluate(fixed, cleared_policy(fixed), "public-release")
        self.assertTrue(allowed["allowed"], allowed["atom_reasons"])

    def test_deliberate_misread_needs_an_author_rule_for_public_output(self):
        misread = atom(self.combos, "misread-synthetic-1")["atom_id"]
        policy = cleared_policy(self.combos)
        policy["machine_misread"] = {"status": "unresolved"}
        report = evaluate(self.combos, policy, "public-release")
        self.assertIn("machine-misread:unresolved-author-rule", report["atom_reasons"][misread])
        policy["machine_misread"] = {"status": "cleared"}
        report = evaluate(self.combos, policy, "public-release")
        self.assertNotIn(misread, report["atom_reasons"])

    def test_combination_fixture_is_allowed_privately(self):
        report = evaluate(self.combos, self.derived, "private-local")
        self.assertTrue(report["allowed"], report["manifest_reasons"])

    def test_combination_lineage_includes_every_input(self):
        cut = atom(self.combos, "cut-synthetic-1")
        closure = sr.lineage_closure(self.combos, cut["atom_id"])
        for input_id in cut["combination"]["input_atom_ids"]:
            self.assertIn(input_id, closure["atoms"])
        self.assertEqual(closure["source_line_ids"], ["diary1-0-0", "diary1-0-1"])
        self.assertEqual(closure["root_source_asset_ids"], ["scan:p/diary1"])

    def test_combination_with_missing_input_is_rejected(self):
        broken = copy.deepcopy(self.combos)
        cut = atom(broken, "cut-synthetic-1")
        cut["combination"]["input_atom_ids"] = ["vf:atom:p001/p001-diary1-0/diary1/line-9-9"]
        cut["lineage"]["input_atom_ids"] = ["vf:atom:p001/p001-diary1-0/diary1/line-9-9"]
        broken = reseal(broken)
        result = sr.verify_manifest(broken)
        self.assertFalse(result["ok"])
        self.assertTrue(any("combination input" in e for e in result["errors"]))

    def test_combination_cycle_is_rejected(self):
        broken = copy.deepcopy(self.combos)
        cut = atom(broken, "cut-synthetic-1")
        cut["combination"]["input_atom_ids"] = [cut["atom_id"]]
        cut["lineage"]["input_atom_ids"] = [cut["atom_id"]]
        broken = reseal(broken)
        result = sr.verify_manifest(broken)
        self.assertFalse(result["ok"])
        self.assertTrue(any("lineage cycle" in e for e in result["errors"]))

    def test_policy_fixtures_all_parse(self):
        for path in sorted(FIXTURES.glob("policy-*.json")):
            policy = load(path)
            self.assertEqual(policy["schema"], sr.POLICY_SCHEMA, path.name)
            self.assertIn("not-a-decision", policy["status"], path.name)


class CliTests(unittest.TestCase):
    def test_check_exit_codes(self):
        base = [sys.executable, str(ROOT / "tools/source_regions.py"), "check",
                "--manifest", str(PILOT), "--policy", str(POLICY)]
        private = subprocess.run(base + ["--scope", "private-local"],
                                 capture_output=True, text=True)
        self.assertEqual(private.returncode, 0, private.stderr)
        public = subprocess.run(base + ["--scope", "public-release"],
                                capture_output=True, text=True)
        self.assertEqual(public.returncode, 3, public.stderr)


class PrivateRegionPreviewTests(unittest.TestCase):
    """Actual T08 inputs through current T02 source and a bounded private package."""
    atom_id = "vf:atom:p001/p001-diary1-0/diary1/line-0-0"

    def setUp(self):
        self.manifest, self.policy = load(PILOT), load(POLICY)

    def copied_source(self, folder):
        repo = folder / "source-checkout"
        for name in ("source/canonical.json", "site/data/j.json", "studio/data/review.json",
                     "studio/data/notes-versions.json", "site/img/p/diary1.jpg"):
            target = repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        return repo

    def selected_source(self, folder):
        """A valid second checkout with distinct JPEG bytes and fresh lineage."""
        import source_foundation as foundation
        repo = self.copied_source(folder)
        image = repo / "site/img/p/diary1.jpg"
        # A trailing technical marker changes the preserved file identity while
        # leaving the source pixels, page size and author geometry unchanged.
        image.write_bytes(image.read_bytes() + b"\nT08 SELECTED CHECKOUT TEST\n")
        canonical = load(repo / "source/canonical.json")
        asset = next(a for a in canonical["assets"] if a["path"] == "site/img/p/diary1.jpg")
        asset.update(sha256="sha256:" + sr.sha256_file(image), bytes=image.stat().st_size)
        (repo / "source/canonical.json").write_text(json.dumps(canonical))
        foundation.rebuild(canonical, repo, write=True)
        manifest = copy.deepcopy(self.manifest)
        manifest["source_assets"][0].update(sha256=sr.sha256_file(image), size=image.stat().st_size)
        manifest = reseal(manifest)
        manifest_path = folder / "selected-manifest.json"
        sr.write_json(manifest_path, manifest)
        return repo, manifest, manifest_path

    def sized_source(self, folder, *, byte_size=None, dimensions=None):
        """Technical boundary fixture; preserve the real checkout and author data."""
        import source_foundation as foundation
        from PIL import Image
        repo = self.copied_source(folder)
        image = repo / "site/img/p/diary1.jpg"
        canonical = load(repo / "source/canonical.json")
        if dimensions is not None:
            with Image.new("RGB", dimensions, "white") as pixels:
                pixels.save(image, format="JPEG")
            page = next(p for p in canonical["pages"] if p["id"] == "diary1")
            page["studio"].update(w=dimensions[0], h=dimensions[1])
            page["reader"].update(iw=dimensions[0], ih=dimensions[1], W=dimensions[0], H=dimensions[1])
        if byte_size is not None:
            original = image.read_bytes()
            self.assertGreaterEqual(byte_size, len(original))
            # JPEG permits trailing bytes; only this temporary technical copy
            # receives padding, with both lineage records refreshed below.
            image.write_bytes(original + b"\0" * (byte_size - len(original)))
        asset = next(a for a in canonical["assets"] if a["path"] == "site/img/p/diary1.jpg")
        asset.update(sha256="sha256:" + sr.sha256_file(image), bytes=image.stat().st_size)
        (repo / "source/canonical.json").write_text(json.dumps(canonical))
        foundation.rebuild(canonical, repo, write=True)
        manifest = copy.deepcopy(self.manifest)
        manifest["source_assets"][0].update(sha256=sr.sha256_file(image), size=image.stat().st_size)
        return repo, reseal(manifest)

    def source_file_hashes(self, repo):
        return {p.relative_to(repo).as_posix(): sr.sha256_file(p)
                for p in repo.rglob("*") if p.is_file()}

    def assert_preview_refusal_preserves_files(self, manifest, policy, repo, folder, message, *, atom_id=None):
        atom_id = self.atom_id if atom_id is None else atom_id
        before = self.source_file_hashes(repo)
        untouched = copy.deepcopy((manifest, policy))
        missing = folder / "must-not-create" / "preview"
        with self.assertRaisesRegex(ValueError, message):
            sr.export_private_preview(manifest, policy, atom_id, missing, repo=repo)
        self.assertFalse(missing.parent.exists())
        prior = folder / "prior-preview"
        prior.mkdir()
        (prior / "sentinel.bin").write_bytes(b"preserved earlier preview\0")
        old = self.source_file_hashes(prior)
        with self.assertRaises(ValueError):
            sr.export_private_preview(manifest, policy, atom_id, prior, repo=repo)
        self.assertEqual(self.source_file_hashes(prior), old)
        self.assertEqual(self.source_file_hashes(repo), before)
        self.assertEqual((manifest, policy), untouched)

    def test_private_preview_accepts_exact_file_byte_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            repo, manifest = self.sized_source(folder, byte_size=16 * 1024 * 1024)
            before = self.source_file_hashes(repo)
            out = folder / "preview"
            sr.export_private_preview(manifest, self.policy, self.atom_id, out, repo=repo)
            package = load(out / "region-preview.json")
            self.assertEqual(len(package["files"]), 5)
            self.assertEqual((out / "assets/source.jpg").stat().st_size, 16 * 1024 * 1024)
            self.assertEqual(self.source_file_hashes(repo), before)

    def test_private_preview_refuses_payload_byte_overflow_before_writes(self):
        for payload in ("image", "policy"):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                repo, manifest = self.sized_source(folder, byte_size=16 * 1024 * 1024 + 1 if payload == "image" else None)
                policy = copy.deepcopy(self.policy)
                if payload == "policy":
                    policy["technical_size_fixture"] = ""
                    base = len((json.dumps(policy, sort_keys=True, ensure_ascii=False,
                                           separators=(",", ":")) + "\n").encode("utf-8"))
                    policy["technical_size_fixture"] = "x" * (16 * 1024 * 1024 + 1 - base)
                self.assert_preview_refusal_preserves_files(manifest, policy, repo, folder, "16 MiB")

    def test_private_preview_aggregate_budget_includes_only_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            repo, manifest = self.sized_source(folder, byte_size=16 * 1024 * 1024)
            policy = copy.deepcopy(self.policy)
            policy["technical_size_fixture"] = ""
            baseline = folder / "baseline"
            sr.export_private_preview(manifest, policy, self.atom_id, baseline, repo=repo)
            baseline_bytes = sum(f["bytes"] for f in load(baseline / "region-preview.json")["files"])
            policy["technical_size_fixture"] = "x" * (32 * 1024 * 1024 - baseline_bytes)
            out = folder / "boundary"
            sr.export_private_preview(manifest, policy, self.atom_id, out, repo=repo)
            package = load(out / "region-preview.json")
            self.assertEqual(sum(f["bytes"] for f in package["files"]), 32 * 1024 * 1024)
            self.assertTrue(all(1 <= f["bytes"] <= 16 * 1024 * 1024 for f in package["files"]))
            self.assertGreater(sum(p.stat().st_size for p in out.rglob("*") if p.is_file()), 32 * 1024 * 1024)
            policy["technical_size_fixture"] += "x"
            self.assert_preview_refusal_preserves_files(manifest, policy, repo, folder, "32 MiB")

    def test_private_preview_manifest_byte_budget_is_inclusive(self):
        import source_foundation as foundation
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo = self.copied_source(folder)
            canonical = load(repo / "source/canonical.json")
            line = next(l for l in canonical["lines"] if l["id"] == "diary1-0-0")

            def reason(value):
                line["geometry"].update(status="unavailable", reason=value)
                (repo / "source/canonical.json").write_text(json.dumps(canonical))
                foundation.rebuild(canonical, repo, write=True)

            value = "TECHNICAL SIZE FIXTURE"
            reason(value)
            baseline = folder / "baseline"
            sr.export_private_preview(self.manifest, self.policy, self.atom_id, baseline, repo=repo)
            # Leave two bytes for decimal-length changes in the geometry file's
            # byte count, then measure the real output to reach the exact edge.
            value += "x" * (64 * 1024 - (baseline / "region-preview.json").stat().st_size - 2)
            reason(value)
            probe = folder / "probe"
            sr.export_private_preview(self.manifest, self.policy, self.atom_id, probe, repo=repo)
            remaining = 64 * 1024 - (probe / "region-preview.json").stat().st_size
            self.assertIn(remaining, (0, 1, 2))
            value += "x" * remaining
            reason(value)
            out = folder / "boundary"
            sr.export_private_preview(self.manifest, self.policy, self.atom_id, out, repo=repo)
            self.assertEqual((out / "region-preview.json").stat().st_size, 64 * 1024)
            reason(value + "x")
            self.assert_preview_refusal_preserves_files(self.manifest, self.policy, repo, folder, "64 KiB")

    def test_private_preview_image_pixel_budget_is_inclusive(self):
        for height, allowed in ((5000, True), (5001, False)):
            with self.subTest(height=height), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                repo, manifest = self.sized_source(folder, dimensions=(8000, height))
                if allowed:
                    out = folder / "boundary"
                    sr.export_private_preview(manifest, self.policy, self.atom_id, out, repo=repo)
                    image = load(out / "region-preview.json")["image"]
                    self.assertEqual(image["width"] * image["height"], 40_000_000)
                else:
                    self.assert_preview_refusal_preserves_files(manifest, self.policy, repo, folder, "40,000,000")

    def test_private_preview_accepts_integer_valued_json_dimensions(self):
        import source_foundation as foundation
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo = self.copied_source(folder)
            canonical = load(repo / "source/canonical.json")
            page = next(p for p in canonical["pages"] if p["id"] == "diary1")
            page["studio"]["w"] = float(page["studio"]["w"])
            page["studio"]["h"] = float(page["studio"]["h"])
            (repo / "source/canonical.json").write_text(json.dumps(canonical))
            foundation.rebuild(canonical, repo, write=True)
            out = folder / "preview"
            sr.export_private_preview(self.manifest, self.policy, self.atom_id, out, repo=repo)
            self.assertEqual(load(out / "region-preview.json")["image"]["width"], page["studio"]["w"])

    def test_private_preview_refuses_boolean_dimension_before_writes(self):
        import source_foundation as foundation
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo, manifest = self.sized_source(folder, dimensions=(1, 1))
            canonical = load(repo / "source/canonical.json")
            page = next(p for p in canonical["pages"] if p["id"] == "diary1")
            page["studio"]["w"] = True  # Python True == 1; reader safe-integer validation rejects it.
            (repo / "source/canonical.json").write_text(json.dumps(canonical))
            foundation.rebuild(canonical, repo, write=True)
            self.assert_preview_refusal_preserves_files(manifest, self.policy, repo, folder, "positive integer dimensions")

    def test_preview_cli_refuses_oversized_package_before_destination_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            repo, manifest = self.sized_source(folder, byte_size=16 * 1024 * 1024 + 1)
            manifest_path = folder / "oversized-manifest.json"
            sr.write_json(manifest_path, manifest)
            before = self.source_file_hashes(repo)
            out = folder / "must-not-create" / "preview"
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/source_regions.py"),
                "preview", "--manifest", str(manifest_path), "--policy", str(POLICY),
                "--atom-id", self.atom_id, "--source-repo", str(repo), "--out", str(out)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
            self.assertIn("16 MiB", result.stderr)
            self.assertFalse(out.parent.exists())
            self.assertEqual(self.source_file_hashes(repo), before)

    def test_private_preview_refuses_unsupported_reader_shapes_before_writes(self):
        for case in ("atom-id", "asset-kind", "asset-tier", "duplicate-page-scan", "block-999", "block-1"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp); repo = self.copied_source(folder)
                manifest = copy.deepcopy(self.manifest)
                selected_id = self.atom_id
                if case == "atom-id":
                    selected_id += "+unsupported"

                    def renamed(value):
                        if isinstance(value, dict):
                            return {k: renamed(v) for k, v in value.items()}
                        if isinstance(value, list):
                            return [renamed(v) for v in value]
                        return selected_id if value == self.atom_id else value

                    manifest = renamed(manifest)
                elif case == "asset-kind":
                    manifest["source_assets"][0]["kind"] = "derived-image"
                elif case == "asset-tier":
                    manifest["source_assets"][0]["tier"] = "m"
                elif case == "duplicate-page-scan":
                    duplicate = copy.deepcopy(manifest["source_assets"][0])
                    duplicate["asset_id"] += ":duplicate"
                    manifest["source_assets"].append(duplicate)
                else:
                    selected = next(a for a in manifest["atoms"] if a["atom_id"] == self.atom_id)
                    selected["source_ids"]["block_index"] = int(case.split("-")[1])
                manifest = reseal(manifest)
                self.assertTrue(sr.verify_manifest(manifest, repo=repo)["ok"])
                self.assertTrue(sr.evaluate(manifest, self.policy, "private-local", release_context={"source_repo": repo})["allowed"])
                self.assert_preview_refusal_preserves_files(manifest, self.policy, repo, folder,
                    "bounded private preview", atom_id=selected_id)

    def test_private_preview_refuses_multiple_current_source_versions_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo = self.copied_source(folder)
            image = repo / "site/img/p/diary2.jpg"
            shutil.copyfile(ROOT / "site/img/p/diary2.jpg", image)
            manifest, policy = copy.deepcopy(self.manifest), copy.deepcopy(self.policy)
            asset = copy.deepcopy(manifest["source_assets"][0])
            asset.update(asset_id="scan:p/diary2", page_id="diary2", path="site/img/p/diary2.jpg",
                         sha256=sr.sha256_file(image), size=image.stat().st_size)
            manifest["source_assets"].append(asset)
            poem = copy.deepcopy(next(a for a in manifest["atoms"] if a["unit"] == "poem"))
            poem.update(atom_id="vf:atom:p002/p002-diary2-0/poem", piece_id="p002",
                        version_id="p002-diary2-0", page_id="diary2", source_asset_ids=["scan:p/diary2"],
                        source_ids={"piece_id": "p002", "version_id": "p002-diary2-0"})
            poem["lineage"].update(root_source_asset_ids=["scan:p/diary2"], source_line_ids=[])
            poem["reading"]["uncertainty_ids"] = []
            manifest["atoms"].append(poem)
            manifest["counts"]["atoms"] += 1
            manifest["counts"]["poems"] += 1
            manifest = reseal(manifest)
            policy["pieces"]["p002"] = {"pool": "unassigned"}
            self.assertTrue(sr.verify_manifest(manifest, repo=repo)["ok"])
            general = sr.evaluate(manifest, policy, "private-local", release_context={"source_repo": repo})
            self.assertTrue(general["allowed"])
            self.assertEqual(len(general["source_bindings"]), 2)
            self.assert_preview_refusal_preserves_files(manifest, policy, repo, folder, "bounded private preview")

    def test_private_preview_refuses_malformed_consumed_policy_before_writes(self):
        cases = ["missing-pool", "unknown-pool", "null-pool", "empty-pool", "array-pool",
                 "null-scopes", "unknown-scopes", "string-scopes", "empty-withheld-asset",
                 "empty-withheld-page", "empty-withheld-version", "empty-veto-atom", "empty-veto-line"]
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp); repo = self.copied_source(folder)
                policy = copy.deepcopy(self.policy)
                piece = policy["pieces"]["p001"]
                if case == "missing-pool":
                    piece.pop("pool")
                elif case.endswith("-pool"):
                    piece["pool"] = {"unknown-pool": "unknown", "null-pool": None,
                                     "empty-pool": "", "array-pool": []}[case]
                elif case.endswith("-scopes"):
                    piece["excluded_versions"].append({"version_id": "unrelated-version",
                        "scopes": {"null-scopes": None, "unknown-scopes": ["unknown"],
                                   "string-scopes": "public-release"}[case]})
                elif case == "empty-withheld-asset":
                    policy["withheld_assets"] = [""]
                elif case == "empty-withheld-page":
                    policy["withheld_pages"] = [""]
                elif case == "empty-withheld-version":
                    piece["withheld_versions"] = [""]
                else:
                    piece["strike_through_vetoes"] = [{"veto_id": "technical-unrelated-veto",
                        "version_id": "unrelated-version", "scopes": ["public-release"],
                        "atom_ids" if case == "empty-veto-atom" else "line_ids": [""]}]
                self.assertTrue(sr.evaluate(self.manifest, policy, "private-local", release_context={"source_repo": repo})["allowed"])
                self.assert_preview_refusal_preserves_files(self.manifest, policy, repo, folder, "private preview policy")

    def test_private_preview_preserves_separate_release_gate_evidence_and_scope_defaults(self):
        for scopes in ("absent", []):
            with self.subTest(scopes=scopes), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                policy = copy.deepcopy(self.policy)
                policy["release_gate"].update(may_publish=True, may_schedule_external_actions=True)
                exclusion = {"version_id": "unrelated-version"}
                if scopes != "absent":
                    exclusion["scopes"] = scopes
                policy["pieces"]["p001"]["excluded_versions"].append(exclusion)
                out = folder / "preview"
                sr.export_private_preview(self.manifest, policy, self.atom_id, out)
                self.assertEqual(load(out / "policy.json"), policy)
                self.assertIs(load(out / "region-preview.json")["mayPublish"], False)
                self.assertIs(load(out / "policy.json")["publication"]["enabled"], False)

    def test_selected_checkout_is_used_by_manifest_validation_and_preview_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo, manifest, _ = self.selected_source(folder)
            tool_image = ROOT / "site/img/p/diary1.jpg"
            tool_hash = sr.sha256_file(tool_image)
            self.assertNotEqual(manifest["source_assets"][0]["sha256"], tool_hash)
            out = folder / "preview"
            descriptor = sr.export_private_preview(manifest, self.policy, self.atom_id, out, repo=repo)
            self.assertEqual((out / "assets/source.jpg").read_bytes(), (repo / "site/img/p/diary1.jpg").read_bytes())
            self.assertEqual(descriptor["mediaDigest"], "sha256:" + manifest["source_assets"][0]["sha256"])
            self.assertTrue(sr.verify_manifest(manifest, repo=repo)["ok"])
            self.assertFalse(sr.verify_manifest(manifest)["ok"])
            self.assertTrue(sr.verify_manifest(self.manifest)["ok"])
            self.assertEqual(sr.sha256_file(tool_image), tool_hash)

    def test_selected_checkout_is_used_by_cli_preloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo, _, manifest_path = self.selected_source(folder)
            base = [sys.executable, "-B", str(ROOT / "tools/source_regions.py")]
            for command, extra in (
                ("check", ["--policy", str(POLICY), "--scope", "private-local"]),
                ("preview", ["--policy", str(POLICY), "--atom-id", self.atom_id, "--out", str(folder / "cli-preview")]),
                ("verify", []),
                ("lineage", ["--atom-id", self.atom_id]),
            ):
                with self.subTest(command=command):
                    result = subprocess.run(base + [command, "--manifest", str(manifest_path), "--source-repo", str(repo)] + extra,
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertEqual((folder / "cli-preview/assets/source.jpg").read_bytes(),
                             (repo / "site/img/p/diary1.jpg").read_bytes())

    def test_selected_checkout_stale_assets_refuse_both_scopes_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo, manifest, manifest_path = self.selected_source(folder)
            bindings = sr.current_source_bindings(manifest, repo=repo)
            digest = "sha256:" + sr.manifest_digest(manifest)
            components = [{"kind": "regions", "id": sr.region_component_id(s["pieceId"], s["versionId"]),
                           **s, "revisionDigest": digest, "fixture": False, "path": "regions.json", "sha256": digest}
                          for s in bindings]
            context = {**release_fixtures.context(bindings, components), "source_repo": repo}
            policy = cleared_policy(manifest)
            for scope in ("private-local", "public-release"):
                self.assertTrue(sr.evaluate(manifest, policy, scope, release_context=context)["allowed"])
            # The tool checkout still has a valid image; it must not mask a stale
            # or corrupted file in the explicitly selected checkout.
            (repo / "site/img/p/diary1.jpg").write_bytes(b"CORRUPTED SELECTED CHECKOUT IMAGE")
            for scope in ("private-local", "public-release"):
                report = sr.evaluate(manifest, policy, scope, release_context=context)
                self.assertFalse(report["allowed"])
                self.assertIn("source-asset bytes changed: scan:p/diary1", report["manifest_reasons"])
            self.assertFalse(sr.verify_manifest(manifest, repo=repo)["ok"])
            with self.assertRaises(ValueError):
                sr.export_private_preview(manifest, self.policy, self.atom_id, folder / "bad-api", repo=repo)
            for command, extra in (
                ("check", ["--policy", str(POLICY), "--scope", "private-local"]),
                ("preview", ["--policy", str(POLICY), "--atom-id", self.atom_id, "--out", str(folder / "bad-cli")]),
            ):
                result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/source_regions.py"), command,
                    "--manifest", str(manifest_path), "--source-repo", str(repo)] + extra, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
                self.assertIn("source-asset bytes changed", result.stderr)
            self.assertFalse((folder / "bad-api").exists())
            self.assertFalse((folder / "bad-cli").exists())

    def test_selected_checkout_linked_asset_is_refused_before_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo, manifest, _ = self.selected_source(folder)
            image = repo / "site/img/p/diary1.jpg"
            outside = folder / "outside.jpg"
            image.rename(outside); image.symlink_to(outside)
            report = sr.verify_manifest(manifest, repo=repo)
            self.assertFalse(report["ok"])
            self.assertTrue(any("unsafe" in message for message in report["errors"]))
            with self.assertRaisesRegex(ValueError, "unsafe"):
                sr.export_private_preview(manifest, self.policy, self.atom_id, folder / "linked", repo=repo)
            self.assertFalse((folder / "linked").exists())

    def test_private_current_source_context_is_not_ignored(self):
        for context in ({"source_snapshots": []}, {"source_repo": "/missing-current-source"},
                        {"current_sources": [{"pieceId": "p001", "versionId": "p001-diary1-0",
                                              "sourceFingerprint": "sha256:" + "f" * 64}]}):
            with self.subTest(context=context):
                result = sr.evaluate(self.manifest, self.policy, "private-local", release_context=context)
                self.assertFalse(result["allowed"])
                self.assertTrue(any(reason.startswith("source-binding:") for reason in result["manifest_reasons"]))

    def test_actual_package_binds_current_source_geometry_policy_and_every_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "preview"
            descriptor = sr.export_private_preview(self.manifest, self.policy, self.atom_id, out)
            package = load(out / "region-preview.json")
            self.assertEqual(package["source"], sr.current_source_bindings(self.manifest)[0])
            self.assertEqual(package["sourceAnchor"]["box"], [0.0416, 0.0137, 0.3278, 0.0467])
            self.assertFalse(package["mayPublish"])
            self.assertEqual(package["image"]["display"], "full-source-image-no-crop")
            listed = {f["path"]: f for f in package["files"]}
            actual = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
            self.assertEqual(actual, set(listed) | {"region-preview.json"})
            for path, record in listed.items():
                self.assertEqual(record["sha256"], "sha256:" + sr.sha256_file(out / path))
                self.assertEqual(record["bytes"], (out / path).stat().st_size)
            self.assertEqual(descriptor["package"]["sha256"], "sha256:" + sr.sha256_file(out / "region-preview.json"))
            geometry = load(out / "geometry.json")
            self.assertEqual(geometry["reviewPageGeometry"]["blocks"][0]["lines"][0]["lineId"], "diary1-0-0")

    def test_unknown_canonical_geometry_never_becomes_the_old_atom_box(self):
        with tempfile.TemporaryDirectory() as tmp:
            for suffix in ("line-2-0", "line-2-3"):
                out = Path(tmp) / suffix
                sr.export_private_preview(self.manifest, self.policy,
                    "vf:atom:p001/p001-diary1-0/diary1/" + suffix, out)
                package = load(out / "region-preview.json")
                self.assertEqual(package["sourceAnchor"]["status"], "unavailable")
                self.assertIsNone(package["sourceAnchor"]["box"])
                self.assertEqual(load(out / "geometry.json")["sourceAnchor"], package["sourceAnchor"])
            self.assertEqual(load(Path(tmp) / "line-2-0/region-preview.json")["sourceAnchor"]["reason"], "block-source-geometry-incomplete")

    def test_changed_atom_or_coordinate_only_geometry_refuses_old_descriptor(self):
        import source_foundation as foundation
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo = self.copied_source(folder)
            original = sr.export_private_preview(self.manifest, self.policy, self.atom_id, folder / "first", repo=repo)
            changed = copy.deepcopy(self.manifest)
            next(a for a in changed["atoms"] if a["atom_id"] == self.atom_id)["region"]["bbox"][0] += 1
            changed = reseal(changed)
            with self.assertRaisesRegex(ValueError, "stale.*descriptor"):
                sr.export_private_preview(changed, self.policy, self.atom_id, folder / "changed-atom", repo=repo, expected=original)
            canonical = load(repo / "source/canonical.json")
            line = next(l for l in canonical["lines"] if l["id"] == "diary1-0-0")
            line["geometry"]["readerRow"][2] += 0.001
            line["geometry"]["studioBox"][0] += 0.001
            (repo / "source/canonical.json").write_text(json.dumps(canonical))
            foundation.rebuild(canonical, repo, write=True)
            with self.assertRaisesRegex(ValueError, "stale.*descriptor"):
                sr.export_private_preview(self.manifest, self.policy, self.atom_id, folder / "changed-geometry", repo=repo, expected=original)
            current = sr.export_private_preview(self.manifest, self.policy, self.atom_id, folder / "fresh-geometry", repo=repo)
            self.assertEqual(current["source"], original["source"])
            self.assertNotEqual(current["geometryDigest"], original["geometryDigest"])
            self.assertFalse((folder / "changed-atom").exists())
            self.assertFalse((folder / "changed-geometry").exists())

    def test_changed_media_scope_and_withholding_refuse_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo = self.copied_source(folder)
            image = repo / "site/img/p/diary1.jpg"
            original = image.read_bytes(); image.write_bytes(original + b"changed")
            with self.assertRaisesRegex(ValueError, "source.asset"):
                sr.export_private_preview(self.manifest, self.policy, self.atom_id, folder / "changed-media", repo=repo)
            image.write_bytes(original)
            for name, manifest, policy in (
                ("changed-scope", {**self.manifest, "scope": {"distribution": "public", "may_publish": True}}, self.policy),
                ("withheld", self.manifest, {**self.policy, "withheld_assets": ["scan:p/diary1"]}),
                ("publishing", self.manifest, {**self.policy, "publication": {"enabled": True}}),
            ):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    sr.export_private_preview(reseal(manifest), policy, self.atom_id, folder / name, repo=repo)
                self.assertFalse((folder / name).exists())

    def test_live_review_or_source_policy_changes_require_a_fresh_descriptor(self):
        import source_foundation as foundation
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); repo = self.copied_source(folder)
            original = sr.export_private_preview(self.manifest, self.policy, self.atom_id, folder / "initial", repo=repo)
            db = folder / "db"
            (db / "reviews").mkdir(parents=True)
            (db / "reviews/diary1-0-0.json").write_text(json.dumps({"status": "corrected", "original": "The walls", "text": "TECHNICAL TEST UPDATED READING", "at": "2026-11-06T00:00:00Z"}))
            canonical, _ = foundation.apply_reviews(load(repo / "source/canonical.json"), db)
            (repo / "source/canonical.json").write_text(json.dumps(canonical))
            foundation.rebuild(canonical, repo, write=True)
            with self.assertRaisesRegex(ValueError, "stale.*descriptor"):
                sr.export_private_preview(self.manifest, self.policy, self.atom_id, folder / "stale-source", repo=repo, expected=original)
            fresh = sr.export_private_preview(self.manifest, self.policy, self.atom_id, folder / "fresh-source", repo=repo)
            self.assertNotEqual(fresh["source"], original["source"])
            (db / "release").mkdir()
            (db / "release/p001.json").write_text(json.dumps({"pool": "reserve", "publicStatus": "private"}))
            with self.assertRaisesRegex(ValueError, "stale.*descriptor"):
                sr.export_private_preview(self.manifest, self.policy, self.atom_id, folder / "stale-policy", repo=repo, db=db, expected=fresh)
            (db / "release/p001.json").write_text(json.dumps({"pool": "reserve", "publicStatus": "withheld"}))
            with self.assertRaisesRegex(ValueError, "withholds"):
                sr.export_private_preview(self.manifest, self.policy, self.atom_id, folder / "withheld-source", repo=repo, db=db)
            for name in ("stale-source", "stale-policy", "withheld-source"):
                self.assertFalse((folder / name).exists())

    def test_private_cli_honors_explicit_current_source_checkout(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/source_regions.py"), "check",
            "--manifest", str(PILOT), "--policy", str(POLICY), "--scope", "private-local",
            "--source-repo", "/missing-current-source"], capture_output=True, text=True)
        # The selected checkout is now checked during manifest preload, so an
        # unreadable source is an input error rather than a later scope refusal.
        self.assertEqual(result.returncode, 2, result.stderr or result.stdout)
        self.assertIn("source-asset unavailable or unsafe", result.stderr)

    def test_current_source_pixels_are_required_even_with_public_positive_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self.copied_source(Path(tmp))
            context = release_fixtures.regions(self.manifest)
            context["source_repo"] = repo
            policy = cleared_policy(self.manifest)
            self.assertTrue(sr.evaluate(self.manifest, policy, "public-release", release_context=context)["allowed"])
            image = repo / "site/img/p/diary1.jpg"
            image.write_bytes(image.read_bytes() + b"CHANGED TECHNICAL SOURCE PIXELS")
            for scope in ("private-local", "public-release"):
                with self.subTest(scope=scope):
                    report = sr.evaluate(self.manifest, policy, scope, release_context=context)
                    self.assertFalse(report["allowed"])
                    self.assertIn("source-asset bytes changed: scan:p/diary1", report["manifest_reasons"])


if __name__ == "__main__":
    unittest.main()
