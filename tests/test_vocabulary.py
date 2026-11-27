"""Tests for tools/vocabulary.py (journal-handwritten-web #56).

Synthetic fixtures only: invented two-page journals, never real poem text.
The committed-file tests read the real site/data/j.json and
studio/data/vocabulary.json to prove the committed counts are a fresh
recount, not a trusted number.
Run from anywhere:  python3 -m unittest discover -s tests -v
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import vocabulary  # noqa: E402


def _page(pid, lines, u=None):
    return {"id": pid, "B": [{"t": 0, "L": lines, "g": [0] * len(lines), "v": 0}],
            "u": u or []}


def _journal(pages):
    return {"v": 2, "pages": pages, "pieces": []}


class TokenizeTests(unittest.TestCase):
    def test_lowercase_fold_and_punctuation_stripped(self):
        self.assertEqual(vocabulary.tokenize("The Walls, collapse!"),
                         ["the", "walls", "collapse"])

    def test_hyphenated_word_is_one_form(self):
        self.assertEqual(vocabulary.tokenize("well-known sea-change"),
                         ["well-known", "sea-change"])

    def test_em_dash_splits_words(self):
        self.assertEqual(vocabulary.tokenize("sown—letters read"),
                         ["sown", "letters", "read"])

    def test_apostrophe_kept_mid_word_stripped_at_edges(self):
        self.assertEqual(vocabulary.tokenize("don't 'beasts' 'g'"),
                         ["don't", "beasts", "g"])

    def test_non_letter_forms_are_not_words(self):
        self.assertEqual(vocabulary.tokenize("17 136-78 1.5.14 - · →"), [])

    def test_markup_fragments_kept_verbatim(self):
        # No silent cleanup: the transcription's own [[struck / ]] fragments
        # stay in the form, and are reported in the output's notes.
        self.assertEqual(vocabulary.tokenize("child[[ins gently[[struck"),
                         ["child[[ins", "gently[[struck"])


class UncertainTests(unittest.TestCase):
    def test_quoted_readings_extracted(self):
        note = "'sown' in line 3 — letters read close to 'soun'"
        self.assertEqual(vocabulary.extract_uncertain_words(note),
                         ["sown", "soun"])

    def test_apostrophe_inside_quoted_span_kept(self):
        note = "'runners' — apostrophe placement unclear ('runner's')"
        self.assertEqual(vocabulary.extract_uncertain_words(note),
                         ["runners", "runner's"])
        self.assertEqual(
            vocabulary.extract_uncertain_words("'you'll' and 'I'll' uncertain"),
            ["you'll", "i'll"])

    def test_multiword_span_tokenizes(self):
        self.assertEqual(
            vocabulary.extract_uncertain_words("'her' in 'fragments of her'"),
            ["her", "fragments", "of", "her"])

    def test_unquoted_note_contributes_nothing(self):
        self.assertEqual(
            vocabulary.extract_uncertain_words(
                "Beginnings of all lines are not visible in the scan"), [])


class CountTests(unittest.TestCase):
    def test_counts_are_distinct_in_purpose(self):
        journal = _journal([
            _page("pg1", ["The walls collapse", "youve sown:"],
                  u=["'sown' in line 3 — letters read close to 'soun'"]),
            _page("pg2", ["The walls return"], u=["'perused' — could be 'pursued'"]),
        ])
        counted = vocabulary.count_vocabulary(journal)
        self.assertEqual(counted["confirmed"],
                         {"the", "walls", "collapse", "youve", "sown", "return"})
        self.assertEqual(counted["uncertain_only"],
                         {"soun", "perused", "pursued"})
        self.assertEqual(counted["lines"], 3)
        self.assertEqual(counted["uncertain_notes"], 2)
        self.assertEqual(counted["quoted_spans"], 4)

    def test_recount_determinism(self):
        journal = _journal([_page("pg1", ["Sea-change, well-known walls"])])
        doc1 = vocabulary.build(journal, jjson_sha256="0" * 64,
                                generated_at="2026-11-27T00:00:00Z")
        doc2 = vocabulary.build(journal, jjson_sha256="0" * 64,
                                generated_at="2026-11-27T00:00:00Z")
        self.assertEqual(json.dumps(doc1, indent=2, sort_keys=True),
                         json.dumps(doc2, indent=2, sort_keys=True))
        self.assertEqual(doc1["counts"]["confirmed"], 3)


class CommittedFileTests(unittest.TestCase):
    def test_committed_counts_match_fresh_recount(self):
        jjson = ROOT / "site/data/j.json"
        vocab_path = ROOT / "studio/data/vocabulary.json"
        self.assertTrue(vocab_path.is_file(), "vocabulary.json not generated")
        raw = jjson.read_bytes()
        words, uncertain_only, doc = vocabulary.load_vocabulary(vocab_path)
        self.assertEqual(doc["generated_from"], hashlib.sha256(raw).hexdigest())
        counted = vocabulary.count_vocabulary(json.loads(raw))
        self.assertEqual(len(words), len(counted["confirmed"]))
        self.assertEqual(words, counted["confirmed"])
        self.assertEqual(uncertain_only, counted["uncertain_only"])
        self.assertEqual(doc["counts"]["confirmed"], len(counted["confirmed"]))
        self.assertEqual(doc["counts"]["uncertain_only"], len(counted["uncertain_only"]))
        self.assertEqual(doc["counts"]["with_uncertain"],
                         len(counted["confirmed"] | counted["uncertain_only"]))

    def test_no_uncertain_only_word_in_confirmed(self):
        words, uncertain_only, _ = vocabulary.load_vocabulary(
            ROOT / "studio/data/vocabulary.json")
        self.assertFalse(words & uncertain_only)

    def test_in_vocabulary_answers_from_committed_list(self):
        words, _, _ = vocabulary.load_vocabulary(ROOT / "studio/data/vocabulary.json")
        self.assertTrue(vocabulary.in_vocabulary("walls", words))
        self.assertTrue(vocabulary.in_vocabulary("Walls", words))
        self.assertFalse(vocabulary.in_vocabulary("quuxxyzzy", words))
        self.assertFalse(vocabulary.in_vocabulary("", words))
        self.assertFalse(vocabulary.in_vocabulary("two words", words))

    def test_cli_reproduces_committed_file(self):
        vocab_path = ROOT / "studio/data/vocabulary.json"
        doc = json.loads(vocab_path.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "vocabulary.json"
            proc = subprocess.run(
                [sys.executable, str(TOOLS / "vocabulary.py"),
                 "--jjson", str(ROOT / "site/data/j.json"),
                 "--out", str(out),
                 "--generated-at", doc["generated_at"]],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(out.read_bytes(), vocab_path.read_bytes())


class PoolTests(unittest.TestCase):
    def test_reader_cut_pool_keeps_series_only(self):
        pools = {"p001": "series", "p002": "reserve", "p003": "archive",
                 "p004": "unsorted", "p005": "unknown", "p006": "series"}
        got = vocabulary.reader_cut_pool(
            ["p001", "p002", "p003", "p004", "p005", "p006"], pools.get)
        self.assertEqual(got, ["p001", "p006"])

    def test_reader_cut_pool_uses_withheld_definition(self):
        # Every non-Series pool in cut_up.WITHHELD_POOLS is dropped, not
        # just Reserve — the same definition #65's shared-scan rule uses.
        for pool in ("reserve", "archive", "unsorted", "unknown"):
            self.assertEqual(vocabulary.reader_cut_pool(["p1"], lambda _p, p=pool: p), [])

    def test_pool_of_from_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pools.json"
            path.write_text(json.dumps({"pools": {
                "p001": {"pool": "series"}, "p002": {"pool": "reserve"}}}))
            pool_of = vocabulary.pool_of_from_map(path)
            self.assertEqual(pool_of("p001"), "series")
            self.assertEqual(pool_of("p002"), "reserve")
            # Absent from the map: no release document, i.e. unsorted.
            self.assertEqual(pool_of("p099"), "unsorted")

    def test_committed_pool_map_excludes_reserve(self):
        pool_of = vocabulary.pool_of_from_map(ROOT / "site/data/pools.json")
        data = json.loads((ROOT / "site/data/j.json").read_text())
        ids = [p["id"] for p in data["pieces"]]
        kept = vocabulary.reader_cut_pool(ids, pool_of)
        # The committed map names only p001-p005, all Series; every other
        # piece is unsorted today and therefore withheld from the pool.
        self.assertEqual(kept, ["p001", "p002", "p003", "p004", "p005"])


if __name__ == "__main__":
    unittest.main()
