# T10 verification and handoff receipt

**Outcome: one private, explicitly labeled technical realization round-trips through storage and preview.** The reusable glyph worksheet/import path is implemented. This validates the tooling, not an author decision to adopt English/Latin as a study language, Greek-first, an expanded font, a finished translation, or publication.

Review baseline: **2026-11-05**. Execution/evidence instants are **2026-11-06 UTC**, still November 5 in the repository's America/New_York session-log convention. Base: `038d01fb1862f2e569d231b5b3c4c3a4eb1aecda`. Branch: `t10/script-realization-glyphs-2026-11-05`. The exact final remote head and draft PR identity belong to the PR handoff/readback; this directory records the tested bytes and inputs without attempting a self-referential commit hash.

## Inspect the deliverable

| Artifact | What it establishes |
|---|---|
| [Pilot realization](pilot/realization.json), [immutable revision](pilot/store/t10-latn-fixture-r1.json) | Existing `p001` / `p001-diary1-0`; 22 exact source lines; original/corrected readings and review-record hashes; own realization identity, method, actor, history, language/script/layout, glyph source and private visibility. |
| [Pilot preview](pilot/index.html), [report](pilot/report.json) | Existing English/Latin reading and original font, with no translated or generated poem text. Source fingerprint `sha256:5de0901485952e6ad279fce6ea102af4f830f2a4813e82842a90ebcc3d8d217a`; revision digest `sha256:15433dc21b334d64df46d62432f9a4a31d25574351872f39b3aee248e8f719a1`. |
| [Public projection](pilot/public-projection.json) | Zero records and no private identifiers, exclusions, source snapshots or assets. A real T03 clearance adapter is still required before public output can exist. |
| [Capture worksheet](capture-sheet.html) | 37 exact source sequences, three blank drawing slots each, explicit scalars, guides and provenance. This is a reusable template, not a request to redraw the whole alphabet or proof that glyphs were supplied. |
| [Capture input](glyph-input/capture.json), [source PNG](glyph-input/font-derived-capture.png), [imported manifest](glyph-proof/manifest.json), [proofsheet](glyph-proof/preview.html) | One existing-font-derived U+0054 raster was imported and cropped, with source/rectangle/scalar/byte provenance preserved. It is not a scan, new handwriting or an approved shape. Original input is retained alongside the derived crop. |
| [Glyph report](glyph-report.json), [font audit](font-audit.json) | Actual CLI source/export binding, private import, original OTF hash, coverage/tables, and separate crop/manifest hashes. |
| [Schema](../../../schemas/script-realization.schema.json), [schema review](schema-review.json) | Syntax contract plus semantic validation. Local schema references and fixture validation passed. No independent Draft 2020-12 engine was available; that narrower limitation is explicit. |
| [Source preservation](source-preservation.json), [code hashes](code-hashes.json) | 559 pre-existing scoped files byte-identical to the base; exact SHA-256 of the six new code/schema/test files used by final checks. |
| [Reproduction](reproduction.json) | Regenerating with the preserved font and recorded instant produced all six pilot files byte for byte. |

Start with the [design and commands](../../t10-script-realizations.md), [glyph workflow](../../t10-glyph-workflow.md), [integration and issue disposition](../../integration/t10-handoff.md), [policy audit](../../t10-policy-followups.md), and [remaining author choices](../../t10-author-decisions.md).

## Rendering evidence

The final [browser report](browser/browser.json) contains **six passing cases**. The four poem cases use 1280×960 desktop and 390×844 touch emulation, each in light and dark. Every case preserves all 22 logical source lines and the recorded `lang`, `dir` and writing mode, loads and actually uses the custom author font, has no horizontal overflow, keeps the metadata panel hidden, and makes no external requests or runtime exceptions. The closed details control does not cover the source lines.

| View | Evidence |
|---|---|
| Desktop / light | [Screenshot](browser/desktop-light.png) |
| Desktop / dark | [Screenshot](browser/desktop-dark.png) |
| Phone size / light | [Screenshot](browser/phone-light.png) |
| Phone size / dark | [Screenshot](browser/phone-dark.png) |
| Unicode and provenance panel | [Screenshot](browser/unicode-and-provenance.png) |
| Blank glyph capture sheet | [Screenshot](browser/capture-sheet.png) |
| Imported glyph proof | [Screenshot](browser/glyph-proof.png) |

The diagnostic `U+0041 U+0301` stays two scalars and the precomposed `U+00C1` stays one. Each is an intact text run. Their observed shaped widths agree; the actual fallback face is DejaVu Serif. This diagnostic is separate from the poem and is not added to the author font. The poem itself has no missing cmap scalars in the supplied font. Its historical internal family name remains private and unchanged; CSS uses `ajp-scribbles`.

The sheet case confirms 37 rows and 111 empty drawing cells. The proof case confirms the one crop image decodes, source hash/private labels are present, and there is no horizontal overflow. Screenshots were visually inspected. The sheet's A4 print stylesheet is supplied; physical printer behavior/pagination was not separately certified.

**Limits:** Chromium 153.0.8010.0 on Linux; touch emulation is not a physical iPhone or Safari test. Only the existing Latin realization is accepted as a technical fixture. No Greek, Hebrew, Arabic, Indic, joined-script or vertical-layout quality is established. Language/script metadata checks syntax, not linguistic validity. Python's Unicode database is 15.0.0; this is not a current-Unicode conformance suite. Full versions are in [runtime.json](runtime.json).

## Validation results

| Check | Result and evidence |
|---|---|
| Final realization tests | **17 pass**, [log](realization-tests.log): exact round trip, source/script change distinction, immutable history/fork refusal, active-writer lock, source rebinding, line identity, mode/authorship, HTML escaping, asset-byte changes, protected destinations and visibility exclusion. |
| Final glyph tests | **12 pass**, [log](glyph-tests.log): actual export vs declared policy/fingerprint, Reserve/withheld rejection across all derivative CLIs, stale corrections, exact scalars, crop hashes/pixels, geometry, malformed JSON, traversal, symlinks, bounds and no overwrite. |
| Wider Python suite | **173 run, 172 pass, one skip**, [log](repository-tests.log), with fontTools/Brotli enabled. This run included the then-current 16 realization tests. The later storage-lock and glyph CLI changes were verified by the final focused suites above. No failures are hidden; negative posting tests intentionally print refusal messages. |
| Skip | Existing test cannot simulate missing system fontTools because fontTools is installed. An earlier run used an unavailable interpreter path and skipped font tests; that run was replaced by the recorded font-enabled run and is not the passing evidence. |
| Repository integrity gate | [Log](integrity.log): **509 references checked, zero missing; 511 checksum entries; OK**. No manifest rewrite was needed. |
| Browser acceptance | **6/6 pass**, with actual font/fallback observations and inspected screenshots. |
| Exact fixture reproduction | **6/6 files byte-identical**, including store, backup, preview, report, public DTO and font. |
| Protected source preservation | **559/559 existing files byte-identical**, no extra untracked files under the inspected reader/studio/release/export/workflow/publication-tool scopes. |

The independent bounded code review inspected source/revision validation, storage preflight/order, exclusions, asset checks and preview behavior. It identified the same concurrent distinct-ID append risk that the primary engineer found; the final implementation serializes restore with a nonblocking POSIX directory lock, tested against a held lock. The reviewer did not independently run the suite or certify the final lock. A separate policy review checked the final audit for date/eligibility overclaims and found none. These reviews are bounded, not an exhaustive security audit or author acceptance.

Visual/technical corrections during verification included waiting for browser paint before measuring a newly opened fallback panel, moving a control out of the narrow poem layout, collapsing `..` before protected-output checks, exact source-commit locator correction, and binding the glyph CLI to actual source policy. Final evidence is from the corrected outputs.

## Reproduce locally

Use Python with fontTools and Pillow; the existing wider suite additionally requires its fontTools/Brotli interpreter. Restore uses POSIX advisory locking. Use a new private destination for each run.

```sh
python3 tools/script_realizations.py validate docs/verification/t10-2026-11-05/pilot/realization.json
python3 tools/script_realizations.py fixture \
  --db exports/studio-db-2026-11-05 \
  --font docs/verification/t10-2026-11-05/pilot/assets/font-ca96121b6e1425012825ef97f9d876d0d6bfe9ba7fb5b5b20bcab99fc9e99fbc.otf \
  --source-locator file_0000000062ec81f5bd6460094274fc8e \
  --at 2026-11-06T01:44:21Z --out /tmp/t10-new-pilot

python3 tools/glyph_workflow.py sheet /tmp/t10-new-sheet.html \
  --text-file docs/verification/t10-2026-11-05/glyph-input/source-reading.txt \
  --provenance docs/verification/t10-2026-11-05/glyph-input/provenance.json \
  --language en --script Latn --db exports/studio-db-2026-11-05
python3 tools/glyph_workflow.py import-capture \
  docs/verification/t10-2026-11-05/glyph-input/capture.json /tmp/t10-new-crops \
  --db exports/studio-db-2026-11-05

python3 -m unittest discover -s tests -p test_script_realizations.py -v
python3 -m unittest discover -s tests -p test_glyph_workflow.py -v
python3 tools/check.py
node tools/verify_script_realizations.mjs \
  --pilot docs/verification/t10-2026-11-05/pilot \
  --glyph-root docs/verification/t10-2026-11-05 \
  --chrome /path/to/chromium --out /tmp/t10-new-browser-evidence
```

The browser harness temporarily serves only the supplied local directories on loopback. No public server is started. Compare code/input hashes before treating a repeat run as the same verification.

## Lifecycle and unresolved choices

The checkout was isolated from the already existing worktrees. Its base is a shallow clone at the exact refreshed main; no claim of complete remote history or repository-wide cleanup is made. Existing ownership and other work were preserved. The chosen draft branch is retained for review; no branch deletion, rebase, merge, deployment, publication, account change, issue closure or external message belongs to this task. The repository's Pages workflow is manual; it is not invoked.

Git's direct HTTPS transport had no usable credential in this runtime. The draft handoff therefore uses the authorized GitHub connector for immutable blobs/tree/commit and the new branch/PR. The staged tree must equal the returned remote tree before the branch is created; final branch/PR/head readback and local parity are recorded in the PR handoff. No `local-ci` status is posted and no remote CI success is claimed from local tests.

Issues #12 and #33 remain open with no assignees/comments in the refreshed evidence. #12's earlier reader merge/hardening remains completed history; roots/glyphs is the relevant residual. For #33, Greek-first and multi-script font expansion remain proposals. Remaining author input can be one line tied to one existing source version, with language/script/orthography, method and only the required glyphs. A submission target can remain unset. T02 review, any actual T03 release adapter/clearance, and script-specific shaping acceptance remain distinct future steps.

The private shared packet/projection was inaccessible; all conclusions use accessible repository, supplied-file and first-party web evidence. Historical approvals are not reused as authority.
