# T10 private glyph capture workflow

Status: implemented technical preparation; author glyph review and any new language choice remain pending. This tool does not create a translation, recognize handwriting, build a font, recover the absent `ingest_fillin.py`, or establish acceptance of Greek or any other proposed script. The bounded English/Latin pilot and its source/version association are documented in [t10-script-realizations.md](t10-script-realizations.md).

## Boundaries and interfaces

`tools/glyph_workflow.py` produces three kinds of private evidence: a blank printable capture sheet, a byte-preserving font copy with a preview, and explicitly labeled PNG crops with a proofsheet. It has no publication or export command. Canonical poems and source fonts are never modified.

Each derivative requires an exact source piece ID, editorial version ID, source hash, source locator, source visibility, source collection and a declared actor/role/evidence. The standalone CLI verifies the declaration against the current repository and an explicitly selected studio export before producing any derivative. It reuses `script_realizations.release_policy` and `source_snapshot`: the declared source pool/visibility must exactly match canonical export policy, and the declared hash must match the exact version fingerprint including exported corrections. An actual Reserve, Archive or withheld source is excluded even if the declaration says private/unsorted.

The low-level Python derivative APIs accept **caller-verified provenance**. Call `verify_source(provenance, repo, db)` first, or supply an equivalent verified source association from the realization resolver. A crop's original PNG hash and rectangle are checked against the supplied bytes; the visible character represented by those pixels is not inferred or verified. Verifying source provenance does not assert that arbitrary caller-supplied specimen text is the exact poem text; the realization layer owns that association.

The allowed derivative visibility is `private`. Source collection uses the same exact lowercase vocabulary as the realization pilot: `series`, `reserve`, `archive`, `unsorted`; only `series` and `unsorted` may produce derivatives here. Withheld sources, Reserve/Archive sources, unknown states, noncanonical spellings and withheld/nonprivate glyphs cause the entire operation to fail before any output is written. This is a gate on this derivative workflow, not a restriction on separate private backups or preservation. File visibility declarations do not provide operating-system access control.

Outputs cannot overwrite existing files or directories and cannot be placed beneath a path component named `site`, `studio`, `release`, `releases`, `dist` or `public`. All source/output path ancestors must be free of symlinks. Capture paths must remain relative to their input manifest directory. These checks are intended for a local trusted workspace; they do not provide concurrency isolation against another process changing filesystem paths during an operation.

T02/T03 coordination is deliberately narrow:

- The private font preview uses the CSS family alias `ajp-scribbles` and the original font bytes. It does not rename internal font names, expand character coverage or change public font assets. T02/T03 retain ownership of those interfaces and publication decisions.
- A realization may reference the emitted manifest by stable ID, relative asset path and manifest hash. Its asset link uses `kind: "capture-manifest"` although the stored capture report identifies its content as `kind: "glyph-capture"`.
- This utility returns lowercase raw SHA-256 hex strings. The realization asset link adds the `sha256:` prefix where its own schema requires it. Hash the stored `manifest.json` bytes; do not hash the return object's extra runtime fields.
- No T08 atom or LingFrame dependency is introduced. Exact strings, scalar labels, source references and asset hashes suffice for this pilot.

## Available source font: observed audit

Audit of the supplied `25-Etceter4Diary-Regular.otf`, attachment source ID `file_0000000062ec81f5bd6460094274fc8e`, on 2026-11-06 UTC:

| Property | Observed result |
| --- | --- |
| SHA-256 | `ca96121b6e1425012825ef97f9d876d0d6bfe9ba7fb5b5b20bcab99fc9e99fbc` |
| File size | 42,608 bytes |
| Internal family / style | `Etceter4 Diary` / `Regular` |
| Glyph count / Unicode cmap entries | 126 / 78 |
| Substitution table | GSUB present; `DFLT` script tag |
| Positioning table | GPOS absent |
| Character coverage | Basic Latin letters, digits, selected punctuation, space, nonbreaking space and em dash |
| Absent from cmap | Greek, Hebrew, accented Latin letters and combining marks |

These results come from `inspect_font`, not an assumed correspondence between glyph count and Unicode coverage. The internal historic name is evidence about the supplied file and is preserved; it does not rename this journal project. No supplied multi-script glyph set has been established by this audit. The existing embedded site font is a separate asset and must be audited separately if used.

A font-derived capture fixture can rasterize an existing mapped letter from this font and then exercise the PNG crop path. Record `authorship.role: "technical-fixture"`, the engineer as the actor who created that fixture, and evidence that credits the original author font and its source ID/hash. Describe it as a **font-derived technical fixture**, not fresh handwriting, an archival scan, a new glyph or author-approved sequence mapping.

## Python APIs

The implementation uses Python's standard library, `fontTools` for fonts and Pillow for PNG files. WOFF2 decoding additionally needs the fontTools Brotli support available in the project's font tooling environment. No new dependency manifest is added.

```python
inspect_font(path) -> dict

verify_source(provenance, repo, db) -> dict

make_sheet(text, script, language, destination, *, provenance,
           direction="ltr") -> dict

import_font(path, out_dir, *, provenance, text,
            language="en", script="Latn", direction="ltr",
            asset_id="author-font") -> dict

import_capture(manifest_path, out_dir) -> dict
```

`inspect_font` returns actual byte hash, size, internal names, Unicode codepoints/scalar labels, glyph count, font table inventory and GSUB/GPOS presence/script tags. It explicitly records the limits of that evidence.

`verify_source` returns the understood provenance fields only after checking actual canonical source policy and the current exact source-version fingerprint. It requires an explicit export and performs no writes. The CLI calls this guard for `sheet`, `import-font` and `import-capture`. Each of those commands requires `--db`; `--repo` defaults to the checkout containing this tool. `inspect-font` only audits font bytes and does not require a poem/export association.

`make_sheet` writes one HTML file. It returns its path/hash, ordered distinct requested sequences, private visibility and `blank-author-work-required` status. Each sequence has an exact scalar label and three empty drawing cells with baseline/alignment guides. It also provides author, date, scan ID and permission fields. Print layout uses A4 with repeating table headings; inspect the browser print preview before distributing a completed worksheet.

`import_font` writes `source-font.<original-extension>`, `manifest.json` and `preview.html`. The source font is copied byte for byte and its internal names remain unchanged. The report lists scalars absent from the cmap. The preview preserves explicit newlines with `white-space: pre-wrap`, uses the supplied `lang`/`dir`, and falls back to system serif. Coverage is not a visual quality assertion.

`import_capture` writes one RGBA PNG per supplied glyph ID, `manifest.json` and `preview.html`. It returns the stored manifest fields plus `output_dir` and `manifest_sha256`; those two convenience fields are not in the stored manifest. Crops preserve selected pixels and strip PNG metadata. Original PNG bytes are not copied into the output, so preserve the original input separately if needed. Crop and manifest bytes are deterministic for the same input and library versions.

### Shared provenance object

```json
{
  "visibility": "private",
  "source": {
    "piece_id": "p001",
    "version_id": "p001-diary1-0",
    "sha256": "REPLACE_WITH_VERIFIED_SOURCE_VERSION_RAW_SHA256",
    "visibility": "private",
    "collection": "unsorted",
    "locator": "REPLACE_WITH_EXACT_SOURCE_VERSION_LOCATOR"
  },
  "authorship": {
    "actor": "REPLACE_WITH_DECLARED_ACTOR",
    "role": "technical-fixture",
    "evidence": "REPLACE_WITH_OBSERVED_SOURCE_CREDIT_AND_METHOD"
  }
}
```

The placeholder values must be replaced; they are not accepted hashes. The example's private/unsorted source matches the current pilot export; it does not infer public clearance from legacy site inclusion. A new handwriting capture should describe the actual author and capture method instead of copying the fixture's role.

### Capture manifest

Add the following fields to the shared provenance object:

```json
{
  "schema_version": 1,
  "id": "glyph-fixture-a",
  "language": "en",
  "script": "Latn",
  "direction": "ltr",
  "capture": {
    "path": "capture.png",
    "sha256": "REPLACE_WITH_EXACT_PNG_RAW_SHA256",
    "width": 320,
    "height": 160,
    "source_id": "REPLACE_WITH_CAPTURE_SOURCE_ID",
    "locator": "REPLACE_WITH_ORIGINAL_CAPTURE_LOCATOR"
  },
  "glyphs": [
    {
      "id": "g001",
      "sequence": "A",
      "scalars": ["U+0041"],
      "rect": [0, 0, 100, 160],
      "visibility": "private"
    }
  ]
}
```

Rectangles are `[x, y, width, height]` in original PNG pixels; the origin is top left and the right/bottom edges are exclusive. Coordinates and dimensions must be integers, never booleans or floats, and must select a nonempty in-bounds area. Glyph IDs must be unique and filename-safe. `scalars` is optional; when supplied, it must match the exact string. The output always includes scalar labels.

The importer accepts only a single-frame PNG of at most 16 MiB and 40 million pixels, with exact declared dimensions and SHA-256. It permits 1–1024 glyph declarations and sequences up to 32 scalars. It rejects corrupt files, duplicate JSON keys, NaN/Infinity/overflow numbers, path traversal, symlinks, control characters and directional-format characters in sequence labels. HTML text and attributes are escaped. No output directory is created on input validation failure. Successful directory bundles are staged and renamed together.

All imported crops and proofsheet labels use `unreviewed-supplied-labels`. A supplied declaration is not author acceptance, a language identification result, a translation or proof of correct glyph shape.

## Unicode and rendering limits

Text and capture labels retain their original scalar sequences. The tool does not normalize NFC/NFD, transliterate, translate or alter a poem version. For example, `Á` and `A` plus U+0301 are distinct declarations with distinct labels.

The blank sheet groups a base with immediately following combining marks. A space, newline, tab or nonbreaking space resets that association; an orphan combining mark is rejected rather than attached across the boundary. This is a limited base-plus-mark worksheet algorithm, not a general grapheme segmenter or a contextual shaping inventory. Capture manifests may explicitly declare a standalone mark when that is the intended input.

Language and script fields receive syntax checks only, not registry validation. Direction is explicitly `ltr` or `rtl`. Browser shaping, joining, bidi behavior, mark placement, line wrapping and fallback still require representative visual review in the intended browser. GSUB/GPOS presence and cmap entries alone cannot establish correctness. The supplied font's missing combining marks mean a decomposed accent test exercises fallback; it cannot establish native mark attachment in that font.

For a future joined or right-to-left script, obtain author-supplied material and expert review of contextual forms, ligatures, marks and line behavior before treating the worksheet as a sufficient font specification. That future expansion is outside the present fixture.

## CLI and verification

```sh
python3 tools/glyph_workflow.py inspect-font /private/source-font.otf
python3 tools/glyph_workflow.py sheet /private/pilot/sheet.html \
  --text-file /private/pilot/source.txt --provenance /private/pilot/provenance.json \
  --language en --script Latn --db exports/studio-db-2026-11-05
python3 tools/glyph_workflow.py import-font /private/source-font.otf /private/pilot/font \
  --text-file /private/pilot/source.txt --provenance /private/pilot/provenance.json \
  --language en --script Latn --db exports/studio-db-2026-11-05
python3 tools/glyph_workflow.py import-capture /private/pilot/input.json /private/pilot/crops \
  --db exports/studio-db-2026-11-05
python3 -m unittest discover -s tests -p test_glyph_workflow.py -v
```

Run those commands from the source checkout, or supply `--repo /path/to/checkout` and an explicit export path. A newer export may change the canonical policy or fingerprint; update provenance only after resolving that change.

The focused regression suite checks exact scalar preservation, deterministic crop bundles, source hashes and rectangles, byte-preserving font import, internal names, fallback reporting, HTML escaping, three blank drawing repetitions, whitespace/combining boundaries, visibility/source-pool exclusion, malformed JSON, corrupt/oversized inputs, geometry, symlinks/traversal and existing-output preservation. Real temporary repository/export fixtures additionally prove that every derivative CLI command rejects actual Reserve/withheld material despite an unsorted declaration, rejects stale hashes and source-policy mismatches, requires `--db`, and detects fingerprints changed by exported corrections. It uses synthetic test pixels/fonts and does not establish author glyph approval or browser rendering quality. Representative browser evidence belongs to the integrated pilot handoff.

The shared packet `2026-10-16-v1.1` and projection `2026-10-16-v1.1-r2` were inaccessible. No assertion in this workflow is attributed to unseen packet contents.
