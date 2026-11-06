# T08 private pilot — `p001` / `p001-diary1-0`

2026-11-05. One bounded, private, local-only pilot of the shared source-region contract.

**This is evidence, not a release candidate and not artistic approval.** The piece's pool is
`unassigned` because no Series/Reserve/Archive decision exists; the policy allows a private-local
build and refuses public release. No scan, poem text, cipher plaintext or puzzle answer is added to
the repository by this pilot.

## What the pilot is

- Piece `p001`, version `p001-diary1-0`, page `diary1` (one scanned page, 1135×1600).
- The owner's `alive-prototype` atoms artifact is normalised into the shared contract; segmentation
  is reused, not re-run.
- Structure: centered line-length (`building_width_px = 1088`), 6 stanzas, 22 lines, one building.
- Units: poem, stanza, line, word, glyph, mark. The synthetic fixture adds derived combinations.
- Eligibility is evaluated by an external visibility policy, not by the manifest.

## Counts

| Unit | Count |
|---|---|
| atoms | 441 |
| poems | 1 |
| stanzas | 6 |
| lines | 22 |
| words | 86 |
| glyphs | 306 |
| marks | 20 |
| open uncertainties | 3 |
| line atoms with a seam polygon | 22 |
| building width | 1088 px |

The 3 uncertainties are the page's existing `site/data/j.json` notes, carried as `open` and **not
mapped to a specific line** by T08 (the author's note names its own place). Line 13 (`diary1-3-2`)
is recorded as `crop-withdrawn-by-owner-eye-review`. Line `diary1-2-3` has
`author_box.state: missing-in-site-data`.

## Files

| Path | Role |
|---|---|
| `p001.source-regions.json` | the pilot manifest (geometry, ids, methods, lineage, states; no text) |
| `visibility-policy.json` | derived pilot defaults — **not** author decisions |
| `checks/*.json` | generated verification and eligibility reports |
| `fixtures/policy-*.json` | synthetic rejection policies (not decisions) |
| `fixtures/synthetic-combinations.source-regions.json` | synthetic Cut/cipher/borrowed/misread atoms (no text) |
| `evidence/alive-runtime.json` | raw headless reproduction of the owner prototype |
| `evidence/owner-lane.md` | what was reused from the owner lane, and its limits |
| `pilot-manifest.json` | file inventory with sha256 (regenerable) |
| `decision-map.md` | per-issue residual decisions for #32 and #52–#56 |

## Inputs and provenance

| Input | Value |
|---|---|
| owner branch / HEAD | `alive-prototype` / `eece4f5` |
| owner atoms | `proto/alive/atoms-p001.json`, sha256 `ed379ac4…2ffca6` |
| source scan | `site/img/p/diary1.jpg`, sha256 `78c4d85b…ec23b5`, 200203 bytes |
| stable ids | `site/data/j.json` (provisional; T02 contract not located) |
| T03 clearance | draft PR #119 at `8d16284`, **not merged**; evidence, not authority |

The manifest records the atoms artifact hash and commit, the scan hash and the method/derivation
limits. It does not contain the owner's text.

## Reproduce

```sh
# 1. Rebuild from the owner artifact (only if the artifact is available and matches the hash)
python3 tools/source_regions.py build \
  --atoms /path/to/alive-proto/proto/alive/atoms-p001.json \
  --atoms-commit eece4f56ffaae81500aaf94fd18852b2038e06d6 \
  --out docs/pilots/t08-p001/p001.source-regions.json

# 2. Verify structure, hashes, methods, lineage and the no-text rule
python3 tools/source_regions.py verify \
  --manifest docs/pilots/t08-p001/p001.source-regions.json \
  --out docs/pilots/t08-p001/checks/verify.json

# 3. Eligibility: private allowed, public refused
python3 tools/source_regions.py check --manifest docs/pilots/t08-p001/p001.source-regions.json \
  --policy docs/pilots/t08-p001/visibility-policy.json --scope private-local
python3 tools/source_regions.py check --manifest docs/pilots/t08-p001/p001.source-regions.json \
  --policy docs/pilots/t08-p001/visibility-policy.json --scope public-release   # exits 3

# 4. Synthetic fixtures and combination atoms
python3 tools/build_t08_combination_fixture.py
python3 tools/source_regions.py check \
  --manifest docs/pilots/t08-p001/fixtures/synthetic-combinations.source-regions.json \
  --policy docs/pilots/t08-p001/visibility-policy.json --scope private-local

# 5. Contract tests
python3 -m unittest tests.test_source_regions -v

# 6. Owner prototype reproduction (read-only; needs the owner worktree and Chrome)
node tools/t08_reproduce_alive.mjs
```

`check` exits `0` allowed, `3` refused, `2` bad input. Regenerate the file inventory with:

```sh
python3 tools/t08_pilot_manifest.py
```

## Results

| Check | Result |
|---|---|
| `verify` | **ok** — 441 atoms, 1 asset, no text fields, integrity matches |
| private-local | **allowed** (`inherited_pool: unassigned`) |
| public-release | **refused** — no clearance, pool is not Series, piece is not whitelisted |
| reserve fixture (private) | allowed, `inherited_pool: reserve`; public would be refused |
| withheld asset/page | refused in every scope |
| version exclusion | refused for the excluded scope |
| strike-through veto | refused privately when the veto's scope includes it |
| synthetic combinations (private) | allowed, lineage closes |
| synthetic combinations (public) | refused — unassigned, no whitelist, borrowed line without credit style, misread rule unresolved |
| owner prototype | ready; `atlasLeak()` total 0 outside pixels; 22 source line ids; 22 polygons; no console errors |

The public refusal is expected and correct. It is not a bug to work around; it records the missing
author decisions.

## What this proves and what it does not

Proves:

- the contract can carry a real page without copying text;
- lineage closes from glyph to scan for all 441 atoms;
- the eligibility engine refuses the public path and the synthetic hazards for the recorded reasons;
- the owner's segmentation/atlas behaviour reproduces on this machine.

Does not prove:

- that the crops, fonts, strokes or layout are artistically final;
- that word/glyph alignment is correct beyond the in-sample checks;
- publication clearance, ID ownership, reader integration or notes integration;
- any answer to the open artistic questions (see `decision-map.md`).

## Privacy

Serve nothing from this folder. The policy is `private-local`; the scan is a private repository
asset referenced by path/hash. Do not put the manifest, policy or fixtures behind a tunnel or a
public host. The pilot manifest intentionally has no poem text, no cipher plaintext and no answer.
