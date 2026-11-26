# E2E Test Infrastructure — Target CLI Contracts

This file records the external contracts that `tests/e2e_witness/` assumes of the
three integrated repositories. The suite is opaque-box: it never imports target
source code. All target interaction goes through subprocess CLIs, isolated temporary
JHW sandboxes, and isolated external-custody intake directories.

## Execution modes

- `--self-check` (or no target env vars): reference CLI stubs in
  `tests/e2e_witness/stubs.py` plus the real corpus (`site/data/j.json`,
  `source/canonical.json`) and real `tools/check.py`.
- `--tndc-dir <path> --jhw-dir <path>` (or both `E2E_TNDC_DIR` and `E2E_JHW_DIR`):
  strict real-target mode. Setting only one target env var raises
  `TargetContractError` at discovery/config time; there is no silent stub fallback.
- `unittest discover -s tests/e2e_witness -p "test_*.py"` uses the same
  `TargetConfig.from_env()` parser as the standalone runner.

## Fail-closed live-provider rule

In real-target mode, any call that supplies `E2E_STUB_*` or `TNDC_SIMULATE_*` runs
inside an ephemeral `tndc_provider_shim()` context (`tests/e2e_witness/tndc_shims.py`).
The shim writes synthetic provider modules and a fake `osascript` into a
`TemporaryDirectory`, prepends them to the child's `PYTHONPATH`/`PATH`, and redirects
hardcoded `/usr/bin/osascript` calls. With no fixture file the shim exits non-zero;
it never opens a live Photos or Notes store. Tests `T1-F01-*`, `T1-F07-*`, and
`--ocr-only` tests without `E2E_STUB_OCR_TEXT_MAP` stay unshimmed and exercise the
target's real dependencies.

## Target CLI & manifest contracts (Final Milestone alignment)

### M1 — `tool-notes-docs-capture`

- Witness subcommand (`witness` / `harvest`, discovered from `--help`, or
  `--tndc-subcmd` / `E2E_TNDC_SUBCMD`), git-tree override flag
  (`--allow-git-dir-for-tests`, discovered from help, or
  `--tndc-git-override-flag` / `E2E_TNDC_GIT_OVERRIDE_FLAG`).
- Stage 0 preflight: `<subcmd> preflight --json`. Must return a JSON object and no
  private note bodies. Reference-stub keys: `photos_access`, `notes_access`,
  `photos_albums`, `notes_folders`. Real-target keys may instead be `ready`,
  `environment`, `photos`, `notes`. Permission denial must exit non-zero with
  `Full Disk Access` / `Automation` guidance and no Python traceback.
- Stage 1 witness flags: `--out-dir` (default external custody
  `/Volumes/Archive4T/Media/intake/versforms-witnesses`), `--photos-album`
  (repeatable), `--notes-folder` (repeatable), `--max-year`, `--download-missing`,
  `--dry-run`, `--allow-git-dir-for-tests`, `--ocr`, `--ocr-only`.
- Artifacts: `<out-dir>/photo_witnesses.json`, `ios_notes.json`, `ocr_cache.json`,
  mode `0600` inside a `0700` directory; no private keys in public artifacts.
- Existing CLI: `--version`, `--state-dir`, `--output-dir`, `status`,
  `capture notes --dry-run`.

### M2 — `tools/match_witnesses.py`

- Flags: `--intake-dir`, `--j-json`, `--out` (default
  `<sandbox>/source/witness_links.json`), optional `--ocr-cmd` supporting an
  `{intake_dir}` placeholder.
- Missing OCR cache must be a handled error (`ocr`/`cache`/`missing`) or a valid
  artifact — never an unhandled `Traceback (most recent call last):`.

### M3 — `tools/build_chronology.py`

- Flags: `--links`, `--j-json`, `--canonical`, `--out`, `--digitized-at`
  (default `2015-09`).
- Two-Clock invariant: changing `--digitized-at` must not change any piece's
  `chronology` object. `date_basis: "undated"` when there are zero confirmed photo
  anchors.

### M3 — `tools/export_round1_projection.py` (Round 1 alignment)

- Flags: `--chronology`, `--j-json`, `--out-dir`, `--piece` (repeatable),
  `--surface`, `--override-image`, `--no-crop`, `--allow-spread-crop`, `--strict`.
- `--surface <page_id>` selects the source scan `site/img/p/<page_id>.jpg` shared
  by all pieces on that page. With `--override-image <path>`, the named local JPEG
  is used for that export instead; these two flags align on the same `surface_id`
  recorded in `projection_manifest.json`.
- `--no-crop` blocks a co-tenanted export; `--allow-spread-crop` is required for
  spread-exposed surfaces. Without either, co-tenanted exports use
  `CorpusIndex.piece_block_bbox()` (8px pad) and set `isolated_crop: true`.
- Manifest `<out-dir>/projection_manifest.json` keys:
  - `schema: "versforms.round1-projection.v1"`
  - `exports[]`: `piece_id`, `surface_id`, `output_file`, `sha256`,
    `shared_surface`, `isolated_crop`, `crop_box` (`[x0,y0,x1,y1]` within page
    bounds), `dimensions` (`[w,h]`, equal to the on-disk JPEG size).
  - `blocked[]`: `piece_id`, `surface_id`, `reason`.
- For co-tenanted exports the on-disk JPEG must be strictly smaller than the page,
  must match `crop_box`/`dimensions`, and must not geometrically overlap any
  co-tenant's raw ink bounds (a <=32px margin is permitted for naturally
  interleaved pages). Metadata segments (EXIF/XMP/ICC/GPS/IFD1 thumbnail) must be
  stripped.

### Runner overrides

`--tndc-subcmd` (`E2E_TNDC_SUBCMD`), `--tndc-git-override-flag`
(`E2E_TNDC_GIT_OVERRIDE_FLAG`), `--jhw-python` (`E2E_JHW_PYTHON`). In strict
real-target mode the JHW python must be explicit, `<jhw-dir>/.venv/bin/python`, or
an already active virtualenv — never a bare system interpreter.

## Coverage

Tier 1 (70), Tier 2 (68), Tier 3 (16), Tier 4 (8), Negative Controls (7):
169 checks, zero skips.
