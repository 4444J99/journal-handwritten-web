"""tools/notes_sidecar.py must accept a valid sidecar and fail loudly on
a dangling anchor, a stale provenance, or a record the projection would
never emit (journal-handwritten-web #17).

Each test builds a tiny repository in a temporary folder (a copy of
tools/notes_sidecar.py plus the minimum studio/data, site/data it needs)
so nothing under the real site/ or studio/ is touched -- except the final
live-repo test, which runs --check read-only against this checkout.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REAL_TOOL = Path(__file__).resolve().parent.parent / "tools" / "notes_sidecar.py"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class NotesSidecarTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "tools").mkdir()
        (self.root / "site" / "data").mkdir(parents=True)
        (self.root / "studio" / "data").mkdir(parents=True)
        import shutil
        shutil.copy2(REAL_TOOL, self.root / "tools" / "notes_sidecar.py")
        self.j = {"pieces": [{"id": "p001", "V": [{"id": "p001-diary1-0", "P": [["diary1", [0]]]}]}]}
        self.review = {"pages": [{"id": "diary1", "blocks": [
            {"t": "text", "lines": [
                {"id": "diary1-0-0", "tx": "The walls"},
                {"id": "diary1-0-1", "tx": "Collapse, like the seal"},
            ]},
        ]}]}
        self.versions = {"pieces": [{"id": "p001", "V": [
            {"id": "p001-diary1-0", "P": [["diary1", [0]]], "d": None},
        ]}]}
        self.write_sources()

    def tearDown(self):
        self._tmp.cleanup()

    def write_sources(self):
        (self.root / "site" / "data" / "j.json").write_text(json.dumps(self.j))
        (self.root / "studio" / "data" / "review.json").write_text(json.dumps(self.review))
        (self.root / "studio" / "data" / "notes-versions.json").write_text(json.dumps(self.versions))

    def write_sidecar(self, records, provenance=True):
        sources = []
        if provenance:
            for rel in ("studio/data/notes-versions.json", "site/data/j.json"):
                sources.append({"path": rel, "sha256": hashlib.sha256((self.root / rel).read_bytes()).hexdigest()})
        data = {"format": "versforms-notes-sidecar", "version": 1,
                "generatedAt": "2026-11-27T15:33:01.000Z",
                "provenance": {"sources": sources}, "records": records}
        (self.root / "site" / "data" / "notes.json").write_text(json.dumps(data))
        return data

    def record(self, **changes):
        rec = {"id": "note-1", "revisionId": "rev-1", "family": "note", "kind": "footnote",
               "pieceId": "p001", "versionId": "p001-diary1-0", "lineId": "diary1-0-0",
               "word": None, "text": "A copied reading note.",
               "citations": [{"label": "The Waste Land, notes"}],
               "credit": "Anthony James Padavano",
               "poemDate": {"certainty": "unknown", "value": None},
               "noteDate": "2026-11-27", "fixture": False}
        rec.update(changes)
        return rec

    def run_tool(self, *args):
        env = dict(os.environ)
        return subprocess.run([sys.executable, str(self.root / "tools" / "notes_sidecar.py"), *args],
                              capture_output=True, text=True, env=env)

    def test_empty_sidecar_passes(self):
        self.write_sidecar([])
        r = self.run_tool("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Notes sidecar OK", r.stdout)

    def test_valid_records_pass(self):
        self.write_sidecar([
            self.record(),
            self.record(id="note-2", revisionId="rev-2", kind="endnote", lineId="diary1-0-1"),
            self.record(id="note-3", revisionId="rev-3", kind="critical-note", lineId=None),
            self.record(id="note-4", revisionId="rev-4", kind="critical-note",
                        pieceId=None, versionId=None, lineId=None),
            self.record(id="note-5", revisionId="rev-5",
                        word={"quote": "walls", "start": 4, "end": 9}),
        ])
        r = self.run_tool("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_dangling_anchor_fails(self):
        self.write_sidecar([self.record(lineId="diary1-9-9")])
        r = self.run_tool("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a member of", r.stdout)

    def test_unknown_version_fails(self):
        self.write_sidecar([self.record(versionId="p001-diary9-0")])
        r = self.run_tool("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown piece/version", r.stdout)

    def test_word_selector_must_match_the_line(self):
        self.write_sidecar([self.record(word={"quote": "seal", "start": 4, "end": 8})])
        r = self.run_tool("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not match the anchored line", r.stdout)

    def test_stale_provenance_fails(self):
        self.write_sidecar([self.record()])
        # The source moved after the sidecar was generated: the check must
        # fail loudly instead of pointing at the wrong source bytes.
        self.j["pieces"][0]["V"].append({"id": "p001-diary1-1", "P": [["diary1", [0]]]})
        self.write_sources()
        r = self.run_tool("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("stale provenance", r.stdout)

    def test_essay_kind_and_fixture_fail(self):
        self.write_sidecar([self.record(kind="essay")])
        r = self.run_tool("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("kind must be one of", r.stdout)
        self.write_sidecar([self.record(fixture=True)])
        r = self.run_tool("--check")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fixture must be false", r.stdout)

    def test_live_repo_sidecar_passes(self):
        # Read-only check against this checkout: the committed sidecar must
        # match the committed sources.
        r = subprocess.run([sys.executable, str(REAL_TOOL), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Notes sidecar OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
