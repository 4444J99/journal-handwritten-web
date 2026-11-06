#!/usr/bin/env python3
"""Write the synthetic combination fixture used by the T08 tests and contracts.

    python3 tools/build_t08_combination_fixture.py [--out PATH]

The fixture is a copy of the p001 pilot manifest plus four derived atoms:

- an author-operated Cut combination of two source lines;
- a borrowed-line combination with no credit style (expected: public refusal);
- a Key Sheet / book-cipher combination over one word;
- a deliberate-misread combination over one word (rule unresolved).

Everything here is structural and synthetic. It contains no poem text, no
cipher plaintext and no puzzle message. Source atoms come from the committed
pilot manifest, so the fixture is reproducible without the owner worktree.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_regions as sr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs/pilots/t08-p001/fixtures/synthetic-combinations.source-regions.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=ROOT / "docs/pilots/t08-p001/p001.source-regions.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    manifest = sr.read_json(args.manifest)
    version = manifest["piece"]["version_id"]
    page = manifest["piece"]["page_id"]
    piece = manifest["piece"]["piece_id"]
    prefix = f"vf:atom:{piece}/{version}/{page}/combination"
    line0 = f"vf:atom:{piece}/{version}/{page}/line-0-0"
    line1 = f"vf:atom:{piece}/{version}/{page}/line-0-1"
    word = f"{line0}/word-0"

    methods = [
        {
            "method_id": "method:cut-fixture-v1",
            "kind": "author-cut",
            "implementation": "tools/build_t08_combination_fixture.py",
            "status": "synthetic-fixture",
            "parameters": {"operation": "reorder-lines", "language_model": False},
            "limits": [
                "synthetic identities only; no cut-up text is stored",
                "operator is the author; the tool performs no generation",
            ],
        },
        {
            "method_id": "method:key-sheet-fixture-v1",
            "kind": "book-cipher",
            "implementation": "tools/build_t08_combination_fixture.py",
            "status": "synthetic-fixture",
            "parameters": {"key": "page:line:word", "text_source": "author-supplied-only"},
            "limits": [
                "no plaintext, key sheet, clue or solution is present",
                "enciphering a poem needs a separate author clearance",
            ],
        },
        {
            "method_id": "method:misread-fixture-v1",
            "kind": "recorded-misread",
            "implementation": "tools/build_t08_combination_fixture.py",
            "status": "synthetic-fixture",
            "parameters": {"rule": "unresolved"},
            "limits": ["a deliberate misread is not a source uncertainty and is not enabled"],
        },
    ]

    combos = [
        sr.make_combination_atom(
            manifest,
            atom_id=f"{prefix}/cut-synthetic-1",
            input_atom_ids=[line0, line1],
            operation="cut",
            method_id="method:cut-fixture-v1",
            origin_kind="author",
            rule="reorder source lines, then keep or strike; author decides each step",
        ),
        sr.make_combination_atom(
            manifest,
            atom_id=f"{prefix}/borrowed-synthetic-1",
            input_atom_ids=[line0],
            operation="borrowed",
            method_id="method:cut-fixture-v1",
            origin_kind="borrowed",
            credit_required=True,
            credit_style=None,
            source_atom_ids=["vf:atom:external/synthetic/borrowed-line"],
            rule="borrowed line; credit style deliberately absent in this fixture",
        ),
        sr.make_combination_atom(
            manifest,
            atom_id=f"{prefix}/cipher-synthetic-1",
            input_atom_ids=[word],
            operation="cipher",
            method_id="method:key-sheet-fixture-v1",
            origin_kind="author",
            rule="page:line:word key; plaintext supplied by the author",
        ),
        sr.make_combination_atom(
            manifest,
            atom_id=f"{prefix}/misread-synthetic-1",
            input_atom_ids=[word],
            operation="misread",
            method_id="method:misread-fixture-v1",
            origin_kind="author",
            deliberate_misread={
                "rule_id": "synthetic-fixture-rule",
                "status": "unresolved",
                "source": "issue #109 question 1 / issue #56; no author ruling recorded",
            },
            rule="machine misread kept as a labelled state, never as the poem's text",
        ),
    ]

    fixture = sr.add_combinations(manifest, combos, methods)
    fixture["status"] = "synthetic-fixture-for-tests-not-authored-work"
    fixture["scope"]["note"] = (
        "Synthetic combination fixture. No cut-up poem, cipher plaintext or puzzle "
        "message exists here; identities and methods are placeholders for the "
        "author-operated Cut and Key Sheet contracts."
    )
    # The scope note is part of the content digest, so recompute after editing it.
    fixture.pop("integrity", None)
    fixture["integrity"] = {"content_sha256": sr.canonical_sha256(fixture)}

    result = sr.verify_manifest(fixture)
    if not result["ok"]:
        print("\n".join(result["errors"]), file=sys.stderr)
        return 1
    sr.write_json(args.out, fixture)
    print(f"wrote {args.out} ({len(fixture['atoms'])} atoms, {len(fixture['methods'])} methods)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
