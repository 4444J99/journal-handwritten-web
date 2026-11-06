# T10: private script realization and author-glyph pilot

**Technical preparation, with a labeled fixture. No language has been adopted and no translation has been produced.** The implementation is isolated from the reader, studio, editorial data, release list, and publication commands. Start with the [verification receipt](verification/t10-2026-11-05/README.md), [author choices](t10-author-decisions.md), and [integration handoff](integration/t10-handoff.md).

## Scope and source reconciliation

The inspected main was `038d01fb1862f2e569d231b5b3c4c3a4eb1aecda`. Issue [#12](https://github.com/4444J99/journal-handwritten-web/issues/12) has its merge/hardening checklist checked; the residual is the author's later roots-and-glyphs phase. This work does not rebuild that reader work. Issue [#33](https://github.com/4444J99/journal-handwritten-web/issues/33) records the author's desire to learn writing systems using the poems. Greek-first, a weekly cycle, a separate rendering axis, and Greek/Cyrillic/Hebrew font expansion are explicitly suggestions in its [October 28 exchange](chats/2026-10-28-learning-world-scripts/01-world-scripts-research-report.md), not accepted choices. Both issues were open, with no comments or assignees at inspection. Their ownership and status are unchanged.

The accessible October 25/26 and October 28 exchanges, subsequent November 5 session records, current issue/PR state, and a personal-context check did not establish a newer author selection of a first language/script or a supplied realization. The original research artifact is identified in the exchange as `compass_artifact_wf-f7b97f4f-9697-5179-b290-8197dd9b3fc0_text/markdown`, version `01a184d7-2c67-7011-9f25-a7536d79c2fc`. The accessible uploaded research copy has source ID `file_000000000ccc81f79f98466cb567e8c6`; it is research, not an instruction to select its recommendations.

Shared packet `2026-10-16-v1.1` / sanitized projection `2026-10-16-v1.1-r2`, private project `g-p-6a10bcb4ada4819194e881431212101a`, remained inaccessible. No claim here relies on its unseen contents. Historical approvals are evidence, not current execution authority.

### The one bounded fixture

| Field | Value and epistemic status |
|---|---|
| Source | Existing `p001` / `p001-diary1-0`, its exact `V[].P` membership, and 22 existing studio line IDs. |
| Selection | Engineering fixture, consistent with the earlier T03 candidate. Not the author's first-poem/final-version choice. |
| Language/script | `en` / `Latn`: the existing source reading. Does not select a new study language. |
| Mode | `visual-realization`, with method `unchanged-source-fixture`. Neither translation nor transliteration. |
| Text | Exact source readings plus applicable existing exported corrections; original readings and review-record hashes remain in the snapshot. No added poem, caption, interpretation, or corrected wording. |
| Source binding | `sha256:5de0901485952e6ad279fce6ea102af4f830f2a4813e82842a90ebcc3d8d217a`, independently matched against T05's proposed implementation. |
| Glyph input | Supplied existing OTF, source ID `file_0000000062ec81f5bd6460094274fc8e`, SHA-256 `ca96121b6e1425012825ef97f9d876d0d6bfe9ba7fb5b5b20bcab99fc9e99fbc`. Preserved derivative font; not a recovered notebook master or newly drawn glyph set. |
| Visibility | Private. Actual export has no release documents; this stays **unsorted**, not Series. |
| Acceptance | Tooling and rendering checks only. Author acceptance, translation competence, final transcription, language choice, and publication clearance are not inferred. |

The original two-page fill-in PDF is also accessible (`file_00000000bf9481f79683d375b39a82cc`). It is retained unchanged. Issue [#110](https://github.com/4444J99/journal-handwritten-web/issues/110) records that its historical `ingest_fillin.py` is missing and author font extension is optional. The new bounded capture tool does not recover or replace that historical generator: it validates explicit capture labels/rectangles and preserves crops for review, without tracing, font compilation, automatic photo alignment, or extending the font. The four broader missing generators in [#107](https://github.com/4444J99/journal-handwritten-web/issues/107) are likewise outside this change.

## Separate realization history from editorial history

The syntax contract is [schemas/script-realization.schema.json](../schemas/script-realization.schema.json). The semantic validator and storage/preview commands are [tools/script_realizations.py](../tools/script_realizations.py). Both are required: JSON Schema alone cannot prove source membership, immutable history, hashes, or author permission. The language/script patterns check tag syntax, not registry membership or appropriate linguistic usage.

A realization owns an ID and an immutable editorial `pieceId`/`versionId` association. Its revisions contain their own language, script, mode, method, authorship/evidence, logical lines, line-to-source associations, layout, glyph asset hashes, visibility, and timestamps. Each revision preserves a full source snapshot and points to the previous revision's digest. A hash detects byte changes; it is not a signature or a statement by the author.

| Change | Recorded behavior |
|---|---|
| Change glyph/style/layout or the author's realization text | Append `realization-edit`; keep the same editorial source. |
| Change script or language metadata | Append `script-change`; never write to `j.json`, `review.json`, `V`, `top`, `st`, or poem numbering. |
| Edit/correct the source reading | Old realization becomes `source-changed` and is omitted from preview. A deliberate `source-rebind` revision must preserve the old snapshot and explicitly bind the new one. |
| Change both source and script | Require two distinct revisions so the causes remain inspectable. |
| Select a different editorial version | Create another realization associated with that existing version. Do not repurpose the old realization. |
| Withhold a realization | Append a visibility revision; retain historical records in private storage but omit the current work from projections. |
| Change font/capture bytes | Use a new immutable asset path/hash. Reusing the same asset path for different bytes anywhere in the history is rejected. |

Source line IDs come from `studio/data/review.json`, through the exact existing piece/version block membership in `site/data/j.json`. Coordinates are not identifiers. Reordering display geometry does not silently move an anchor. Missing/duplicate IDs, repeated blocks, references outside the source version, stale correction originals, and changed source text are errors or explicit invalidations.

The version fingerprint uses the same sorted-key UTF-8 JSON field set as T05 draft PR [#126](https://github.com/4444J99/journal-handwritten-web/pull/126): `{pieceId, versionId, members, lines:[{lineId,text,blockType}]}`. It is a proposed cross-tranche contract, not claimed T02 agreement. Raw readings, correction evidence, and source-file hashes are additionally retained. A display-coordinate-only change is not a new textual version. A normalization-only change still changes the exact stored bytes and is detectable; the tool does not normalize author's text on ingestion.

The `translation`, `transliteration`, and `visual-realization` modes are distinct enumerated values. Human-supplied work requires a realizer credit and evidence locator in addition to the source author. No command supplies a translation or transliteration algorithm. The fixture method validates that all lines and stanza boundaries are copied exactly; it cannot be relabeled as a completed translation.

## Storage and local review

The private store contains one immutable JSON file per realization revision. A nonblocking POSIX advisory lock on the store directory serializes restore preflight and append, automatically releases after process exit, and leaves no lockfile. A busy store is refused for retry; this bounded store implementation requires POSIX locking. Restore validates the entire incoming history and the union with existing history before appending. Same-byte retries are idempotent. A different document under an existing revision ID, forked history, absent parents, or a rewritten history prefix is refused. Complete files become visible by an exclusive atomic link; a partially written file is not exposed as a revision. Existing history is never overwritten or deleted.

The JSON backup carries source snapshots, authorship, timestamps, and asset references. **Keep the assets directory with the backup**: JSON references and hashes alone do not preserve font/capture bytes. The supplied fixture packet includes the actual font bytes and verifies them again before preview. New captures remain separately hashed, reviewable assets; they do not become a compiled font merely because a label maps to a Unicode sequence.

Generate the one fixture into a new private directory:

```bash
python3 tools/script_realizations.py fixture \
  --db exports/studio-db-2026-11-05 \
  --font /path/to/the/supplied-author-font.otf \
  --source-locator file_0000000062ec81f5bd6460094274fc8e \
  --at 2026-11-06T01:44:21Z \
  --out /path/to/new-private-pilot
```

The optional `--at` reproduces the exact recorded fixture instant; omitting it uses the current UTC time. It creates `realization.json`, the immutable `store/`, a content-addressed font asset, a private `index.html`, an empty `public-projection.json`, and a technical receipt. It accepts the authentic zero-release export for private inspection while preserving `unsorted`; it does not invoke or weaken the posting CLI's empty-release hard stop.

Round-trip and recheck an existing packet:

```bash
python3 tools/script_realizations.py validate /path/to/pilot/realization.json
python3 tools/script_realizations.py restore /path/to/pilot/realization.json /path/to/new-store
python3 tools/script_realizations.py pack /path/to/new-store /path/to/new-backup.json
python3 tools/script_realizations.py preview /path/to/new-backup.json \
  --db exports/studio-db-2026-11-05 --assets /path/to/pilot \
  --out /path/to/pilot/rechecked-preview.html
```

`preview` re-reads source data, exported corrections, current source pool/visibility, and asset bytes. It refuses a stale or excluded realization before writing. Serve only the generated private directory on loopback if reviewing in a browser. This tool is not deployed studio storage or a production reader integration. The shared live pages and Cloudflare collections remain unchanged.

## Unicode, shaping, line layout, and fallback

The pilot preserves Unicode scalar sequences exactly, including precomposed and decomposed text. Control characters, surrogates, and embedded bidi formatting controls are rejected in lines; explicit logical lines and layout fields carry those functions. ZWJ/ZWNJ are not globally stripped. An author-supplied script requiring joining controls needs the corresponding glyph workflow and script-specific acceptance, rather than an automatic conversion.

The browser receives whole logical lines as escaped text. It handles normal OpenType shaping; the tool does not substitute glyph images character by character, reverse RTL text, or split base-plus-mark sequences into separate spans. `lang`, HTML `dir`, logical `text-align:start`, and `writing-mode` are explicit. Source line/stanza boundaries remain records; ordinary soft wrapping fits a narrow viewport without changing those records. Automatic hyphenation is disabled.

The existing OTF has 126 glyphs, 78 Unicode mappings, and a `calt` GSUB feature. Its cmap covers the complete 22-line fixture. That is coverage evidence, not a claim that every glyph is artistically finished or that all Latin/Greek/Cyrillic/Hebrew text is covered. The original weak-glyph list and author review remain relevant.

If any scalar in a line lacks author-font coverage, the **entire line** uses a system serif fallback, with the missing codepoints recorded in the private metadata panel. This preserves a shaping run and makes the substitution inspectable. A fallback glyph is not recorded as the author's glyph. The private font uses the approved CSS family alias `ajp-scribbles` while retaining the source font bytes and historical internal names; T03 owns the public metadata rename and sign-off.

The separate technical diagnostic compares `U+0041 U+0301` and `U+00C1`. It is not added to the poem. Browser evidence confirms the original sequence survives, each run is intact, equivalent shaped widths are observed, and the actual fallback face is DejaVu Serif in this runtime. Desktop and 390-pixel touch emulation are recorded in light/dark schemes. This is not physical-iPhone, Safari, Greek, Hebrew, complex-Indic, Arabic, or vertical-layout acceptance. The schema can record those layouts; each chosen script needs an actual author input and its own review.

Primary references checked for this work:

- [Unicode UAX #15, revision 58](https://www.unicode.org/reports/tr15/tr15-58.html): normalization and canonical equivalence. Preserving source sequences here is a provenance choice, not a claim that equivalent strings have different linguistic meaning.
- [W3C: structural markup and right-to-left text](https://www.w3.org/International/questions/qa-html-dir.en.html): HTML direction, inherited base direction, and logical alignment.
- [fontTools `TTFont` documentation](https://fonttools.readthedocs.io/en/latest/ttLib/ttFont.html): font tables, metrics, cmap, and the difference between advances and outline bounds.

Runtime versions and the narrower Unicode database used by Python are recorded in the receipt; no claim of a complete current-Unicode conformance suite is made.

## Publication rules and withheld content

T03 draft [PR #119](https://github.com/4444J99/journal-handwritten-web/pull/119) defines `versforms.release-clearance.v1` as a proposed interface with no cleared release record. Its full [contract](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/docs/releases/release-clearance-contract.md) requires exact input/code/output manifests and dated, attributable clearance. Neither a successful render, a Series label, the source's earlier release, nor a private fixture is that clearance.

The current public projection is **always empty** until an actual T03 adapter is implemented against that contract. It includes no excluded IDs, source text, private evidence, asset references, histories, or diagnostic metadata. `public-proposed` is a request for review, not an approved release state. No new public builder, posting command, publication collection, or deployment path is introduced.

Even the bounded private preview excludes Reserve/Archive sources, withheld sources, withheld realizations, withheld glyph assets, invalid source bindings, and unknown policy values. Private backup retains history so withholding does not destroy evidence. Tests check byte exclusion, not CSS hiding. The new files live outside `site/`, `studio/`, and `release/`; the publishing inputs are byte-identical to the base.

T03's eventual exposure manifest must include realized text, source associations permitted in public, the exact glyph/font bytes and metadata, all crops/worksheets/proofs it would ship, and output hashes. No raw whole capture sheet should be emitted just because one crop is approved. Any changed realization, source reading, pool, font, or output bytes invalidates the corresponding clearance. Existing posting findings in [#123](https://github.com/4444J99/journal-handwritten-web/issues/123) are unchanged by this pilot; its publishing execution is not used here.

## Remaining work

The [glyph workflow](t10-glyph-workflow.md) provides the capture/import procedure and its deliberate limits. Its derivative CLI requires an explicit studio export and verifies the real source fingerprint and pool/visibility before writing; a manifest declaration cannot override actual Reserve/withheld status. The supplied blank worksheet has 37 source sequences with three drawing slots each. A separate font-derived U+0054 crop tests import/provenance; it is not fresh author handwriting. The [policy follow-up](t10-policy-followups.md) reconciles the research's actual named examples without selecting submission targets. The [optional weekly worksheet](t10-weekly-practice.md) supplies blank author-work fields tied to this exact candidate. The [handoff](integration/t10-handoff.md) names the T02/T03/T04/T01 boundaries and the inspected LingFrame proposal. A successful fixture validates tooling only; the language study, translation, artistic interpretation, fresh handwriting, and publication decisions remain the author's.
