#!/usr/bin/env python3
"""Journal vocabulary counter + cut-pool guard (journal-handwritten-web #56).

Counts the journal's vocabulary from ``site/data/j.json`` (the measured
source, read-only for this work) and writes the generated
``studio/data/vocabulary.json`` the author's idea-2/idea-4 decisions need.

Two counts, not one — the author has not decided whether machine-misread
uncertain readings count under the no-AI-text rule, so this build must not
bake in an answer:

- Count A (``confirmed``): distinct word forms in the transcribed ``L``
  lines as they stand.
- Count B (``with_uncertain``): Count A plus the words appearing only in
  the per-page ``u`` uncertain-reading notes, listed separately as
  ``uncertain_only`` and never merged into Count A.

Counting rules (documented here and in the output file, because the number
is meaningless without them):

- Lowercase fold; split on whitespace; em-dash and en-dash split words the
  way whitespace does (the journal joins words with them); ASCII hyphens
  stay inside a token, so hyphenated words count as single forms (the
  journal's hyphenation is the author's, not a tokenization artifact).
- Surrounding punctuation is stripped; apostrophes are kept mid-word
  (``don't`` stays one form) and stripped at the edges (``'beasts`` ->
  ``beasts``).
- A form counts as a word only if it contains at least one letter. Pure
  numbers, number ranges (``136-78``), dates (``1.5.14``) and lone
  punctuation (``-``, ``·``, ``•``, ``→``) are not words for the idea-2
  constraint; they are excluded and listed in the output's ``notes``.
- Forms that carry the transcription's own markup fragments (``[[struck``,
  ``]]``, ``/`` alternatives such as ``d/c`` or ``carefully/carelessly``)
  are kept exactly as they appear — no silent cleanup — and counted in
  the output's ``notes`` with examples, so a later hardening pass can see
  the artifact and refine the rule deliberately.
- Uncertain words are the single-quoted candidate readings in the ``u``
  notes (``'sown'`` ... ``'soun'``), tokenized with the same rules. A
  quoted span may hold an apostrophe between two letters (``runner's``,
  ``you'll``), which the span matcher keeps; a span may hold several words
  (``'fragments of her'``), which tokenize separately. Notes with no quoted
  span contribute nothing and are counted in ``notes``.

The pool guard lives here too, as the ``reader_cut_pool`` helper the plan
calls for, because the guard has to exist before any reader-cut pool is
built or the first pool build will leak Reserve lines:

- ``reader_cut_pool(piece_ids, pool_of)`` keeps only pieces whose pool is
  exactly ``"series"``. The caller supplies ``pool_of`` (piece id -> pool
  string); this module never re-implements the exact-value rule.
- The withheld definition is ``cut_up.WITHHELD_POOLS`` — reserve, archive,
  unsorted (no release document) and unknown (a non-exact pool value) — the
  same definition #65's shared-scan rule and #55's cut-up model use. The
  plan's wording says "drops every Reserve piece"; the live codebase's rule
  is the four non-Series pools, and the evidence wins: a pool that let an
  unsorted piece through would launder unclassified text into the public
  site through a cut-up, bypassing the release process.
- ``pool_of_from_map(pools_path)`` builds a ``pool_of`` from the generated
  ``site/data/pools.json`` map (``tools/pools.py``): a piece the map names
  reads its pool; a piece absent from the map has no release document, i.e.
  pool ``"unsorted"``.

Usage:

    python3 tools/vocabulary.py [--jjson site/data/j.json]
                                [--out studio/data/vocabulary.json]
                                [--generated-at 2026-11-27T00:00:00Z]

``--generated-at`` pins the timestamp so a recount reproduces the committed
file byte-for-byte; without it the current UTC time is used.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import cut_up  # noqa: E402  (WITHHELD_POOLS: the single definition of withheld)

# Punctuation stripped from the edges of a token. Apostrophes are in the
# set so a leading/trailing quote is stripped, while a mid-word apostrophe
# survives because strip() only touches the ends.
STRIP_CHARS = " \t\"“”‘’.,;:!?()[]{}<>«»/\\|@#$%^&*_+=~'`"
DASHES = ("—", "–")  # em-dash, en-dash: word separators, not word characters

# A quoted candidate reading in a u note. The span may contain an apostrophe
# between two letters ('runner's', 'you'll') — the lookarounds keep those
# inside the span instead of ending it at the apostrophe.
QUOTED_SPAN = re.compile(r"'(?:[^']|(?<=[A-Za-z])'(?=[A-Za-z]))+'")

GENERATED_BY = "tools/vocabulary.py (journal-handwritten-web #56)"


def tokenize(text):
    """Word forms in ``text`` under the counting rules above."""
    for dash in DASHES:
        text = text.replace(dash, " ")
    out = []
    for raw in text.split():
        word = raw.strip(STRIP_CHARS).lower()
        if word and any(ch.isalpha() for ch in word):
            out.append(word)
    return out


def extract_uncertain_words(note):
    """Candidate readings quoted in one ``u`` uncertain-reading note."""
    words = []
    for span in QUOTED_SPAN.findall(note):
        words.extend(tokenize(span[1:-1]))
    return words


def count_vocabulary(jdata):
    """Count the vocabulary in parsed ``site/data/j.json`` data.

    Returns a dict with the confirmed and uncertain-only word sets plus
    the audit numbers the output file records.
    """
    confirmed = set()
    uncertain = set()
    lines = 0
    excluded = set()
    markup_forms = set()
    slash_forms = set()
    uncertain_notes = 0
    quoted_spans = 0
    unquoted_notes = 0
    for page in jdata.get("pages", []):
        for note in page.get("u") or []:
            uncertain_notes += 1
            spans = QUOTED_SPAN.findall(note)
            if not spans:
                unquoted_notes += 1
            quoted_spans += len(spans)
            for span in spans:
                uncertain.update(tokenize(span[1:-1]))
        for block in page.get("B", []):
            for line in block.get("L", []):
                lines += 1
                for dash in DASHES:
                    line = line.replace(dash, " ")
                for raw in line.split():
                    word = raw.strip(STRIP_CHARS).lower()
                    if not word:
                        continue
                    if not any(ch.isalpha() for ch in word):
                        excluded.add(word)
                        continue
                    confirmed.add(word)
                    if "[[" in word or "]]" in word:
                        markup_forms.add(word)
                    if "/" in word or "#" in word:
                        slash_forms.add(word)
    return {
        "confirmed": confirmed,
        "uncertain_only": uncertain - confirmed,
        "lines": lines,
        "pages": len(jdata.get("pages", [])),
        "excluded_non_letter_forms": excluded,
        "markup_forms": markup_forms,
        "slash_forms": slash_forms,
        "uncertain_notes": uncertain_notes,
        "quoted_spans": quoted_spans,
        "unquoted_notes": unquoted_notes,
    }


def build(jdata, *, jjson_sha256, generated_at=None):
    """The ``studio/data/vocabulary.json`` document for ``jdata``.

    Deterministic for a fixed ``generated_at``: same j.json input
    reproduces the committed file byte-for-byte.
    """
    counted = count_vocabulary(jdata)
    confirmed = counted["confirmed"]
    uncertain_only = counted["uncertain_only"]
    stamp = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    notes = [
        "Counting rules: lowercase fold; split on whitespace (em/en-dash "
        "split too); surrounding punctuation stripped; apostrophes kept "
        "mid-word, stripped at the edges; hyphenated words are single "
        "forms; a form counts only if it contains a letter.",
        f"Excluded {len(counted['excluded_non_letter_forms'])} non-letter "
        "forms (numbers, ranges, dates, lone punctuation — not words for "
        "the idea-2 constraint): "
        + ", ".join(sorted(counted["excluded_non_letter_forms"])),
        f"{len(counted['markup_forms'])} confirmed forms carry the "
        "transcription's own [[struck / ]] markup fragments and are kept "
        "exactly as they appear (no silent cleanup): "
        + ", ".join(sorted(counted["markup_forms"])[:10])
        + (" ..." if len(counted["markup_forms"]) > 10 else ""),
        f"{len(counted['slash_forms'])} confirmed forms carry an internal "
        "/ or # (alternative readings such as d/c, carefully/carelessly) "
        "and are kept exactly as they appear.",
        f"Uncertain words are the single-quoted candidate readings in the "
        f"{counted['uncertain_notes']} per-page u notes "
        f"({counted['quoted_spans']} quoted spans); "
        f"{counted['unquoted_notes']} notes hold no quoted span and "
        "contribute nothing.",
        "Ideas 2 and 4 (new poems limited to journal vocabulary; poem 100 "
        "from poems 1-99) and whether machine-misread readings count under "
        "the no-AI-text rule remain the author's call; this file reports "
        "both counts instead of choosing.",
    ]
    return {
        "generated_from": jjson_sha256,
        "generated_at": stamp,
        "generated_by": GENERATED_BY,
        "counting_rules": (
            "lowercase fold; split on whitespace (em/en-dash split too); "
            "strip surrounding punctuation; apostrophes kept mid-word; "
            "hyphenated words are single forms; a form counts only if it "
            "contains a letter; uncertain words are the single-quoted "
            "candidate readings in the per-page u notes"
        ),
        "counts": {
            "confirmed": len(confirmed),
            "uncertain_only": len(uncertain_only),
            "with_uncertain": len(confirmed | uncertain_only),
            "lines": counted["lines"],
            "pages": counted["pages"],
            "uncertain_notes": counted["uncertain_notes"],
            "quoted_spans": counted["quoted_spans"],
        },
        "words": sorted(confirmed),
        "uncertain_only": sorted(uncertain_only),
        "notes": notes,
    }


def load_vocabulary(path):
    """Load a generated vocabulary file; returns (words, uncertain_only, doc)."""
    doc = json.loads(Path(path).read_text())
    return set(doc["words"]), set(doc["uncertain_only"]), doc


def in_vocabulary(word, words):
    """True when ``word`` (normalized with the counting rules) is in ``words``.

    ``words`` is the confirmed word set, e.g. from ``load_vocabulary``.
    A multi-word or empty query never matches: the oracle answers about
    single word forms only.
    """
    forms = tokenize(word)
    return len(forms) == 1 and forms[0] in words


def pool_of_from_map(pools_path):
    """A ``pool_of`` callable reading the generated ``site/data/pools.json`` map.

    A piece the map names reads its pool; a piece absent from the map has
    no release document, i.e. pool ``"unsorted"`` (tools/pools.py).
    """
    doc = json.loads(Path(pools_path).read_text())
    pools = doc.get("pools", {})

    def pool_of(piece_id):
        entry = pools.get(piece_id)
        return entry.get("pool") if isinstance(entry, dict) else "unsorted"

    return pool_of


def reader_cut_pool(piece_ids, pool_of):
    """Piece ids eligible for a reader-cut pool, in input order.

    Keeps only pieces whose pool is exactly ``"series"``; every other pool
    — reserve, archive, unsorted, unknown (``cut_up.WITHHELD_POOLS``) — is
    dropped before any line sampling, so no cut-up can be built from
    withheld text. The caller supplies ``pool_of`` (piece id -> pool
    string); this module never re-implements the exact-value rule.
    """
    return [pid for pid in piece_ids if pool_of(pid) == "series"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Count the journal's vocabulary.")
    parser.add_argument("--jjson", default=str(ROOT / "site/data/j.json"))
    parser.add_argument("--out", default=str(ROOT / "studio/data/vocabulary.json"))
    parser.add_argument("--generated-at", default=None,
                        help="pin generated_at (UTC, YYYY-MM-DDTHH:MM:SSZ) for a reproducible file")
    args = parser.parse_args(argv)
    jjson_path = Path(args.jjson)
    raw = jjson_path.read_bytes()
    doc = build(json.loads(raw),
                jjson_sha256=hashlib.sha256(raw).hexdigest(),
                generated_at=args.generated_at)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    counts = doc["counts"]
    print(f"wrote {out_path}: confirmed {counts['confirmed']}, "
          f"uncertain-only {counts['uncertain_only']}, "
          f"with-uncertain {counts['with_uncertain']} "
          f"({counts['lines']} lines, {counts['pages']} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
