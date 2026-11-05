# T03: repeatable first-release preparation

Status: technical preparation only. No release has been approved, posted, deployed or filed by T03. This procedure reuses [PR #101](https://github.com/4444J99/journal-handwritten-web/pull/101); it does not replace the posting implementation. The inspected head is `5d111c13764655312c32ddf1b55390198bc7f70c`. Its final selection, review application, public builder, font checks and posting gates are the dependency.

## What the preserved inputs support

`exports/studio-db-2026-11-05/` contains 38 reviews: 22 confirmed lines on `diary1` and 16 corrected lines on `diary62a`. Its decisions, versions, release, batches and rconfig collections are empty. The separate derived-decision export is preserved as evidence and is not silently combined with the studio export. A historical record says those defaults were imported to D1; this preparation has not re-exported that live database.

The source catalog describes 126 pieces. Its 54 complete poems and four complete song lyrics remain recorded classifications, not author-approved release selections. `p001` is the derived first candidate because its first page is `diary1`. Both its candidacy and final version require author confirmation. The current builder chooses `p001-diary1-0` (`V[0]`, configured top) in the absence of a final decision. `p001-diary62a-0` (`V[1]`, last chronological array entry) carries the 16 corrected lines and shares a page with `p126`. Do not silently substitute the last version for the configured top.

## Run the preparation

Use Python with Pillow, fontTools and Brotli. Set `VERSFORMS_FONT_PYTHON` to that interpreter; the existing builder invokes it for the embedded font. The following commands create new private output directories and never write `release/public.json` or studio records:

```sh
export VERSFORMS_FONT_PYTHON=/absolute/path/to/python-with-fonttools-and-brotli
python3 tools/check.py
python3 tools/prepare_release_packet.py \
  --db exports/studio-db-2026-11-05 \
  --candidate p001 \
  --out .post-poem-work/t03-first-release
```

The command executes `post_poem.py --dry-run` against the real export with no overrides, saves its refusal, and separately uses that same implementation's builder for a private inspection artifact. With the preserved export, the actual posting dry run exits **2**: Series and batch gates fail, while all 38 line reviews pass. No database row is fabricated to make those gates pass. The preparation command's own exit 0 means a packet was created; `packet.json.release_clearance` remains `false`.

The output directory must not already exist, and must not overlap source content or database inputs. A failed attempt is retained for inspection; select a new output path after repairing the cause. The first-release helper deliberately refuses a nonempty source whitelist: subsequent releases belong to the existing posting workflow with the accumulated public set reviewed.

## Inspect the result

Serve only the packet locally:

```sh
python3 -m http.server 8873 --bind 127.0.0.1 \
  --directory .post-poem-work/t03-first-release
```

Open `http://127.0.0.1:8873/`. The report links to the real reader under `preview/`, an unapplied whitelist diff, source catalog, first four candidates in recorded page order, a 100-slot tracker with no assigned numbers or dates, and the finite review queue.

**The entire packet is private.** Its comparison view deliberately includes the withheld neighbour to make the exposure inspectable. Only `preview/` is the proposed bounded output, and even that has no release clearance. Do not deploy the packet root. `noindex` is an indexing instruction, not an access boundary.

| Artifact | Meaning |
|---|---|
| `packet.json` | Source revision, tool/input SHA-256 values, actual gate results, selected versions, every proposed public file, image and font metadata, atlas reconstruction checks, explicit non-clearance. |
| `gated-dry-run.txt` | Real `post_poem.py --dry-run` result; no `--force`, `--include-versions`, or shared-scan acceptance was used. Public-clone identity/push paths were not exercised. |
| `preview/` | Nonempty `p001`/`diary1` reader built by PR #101. |
| `comparison-all-versions/`, `comparison-exposure.json` | Private demonstration of the second version's image exposure. The image-exclusion check fails on `diary62a` blocks 3 and 4 (`p126`), even though their transcript text is withheld. |
| `proposed-whitelist.patch` | Reviewable proposal to add only `p001`; it is not applied. It grants no approval. |
| `author-review-queue.json` | Stable source-linked review tasks; original readings, notes, IDs and unresolved decisions are preserved. |
| `source-catalog.json` | All 126 preserved piece records, page order, review counts, selection defaults and missing gates. |
| `release-tracker-100-slots.csv` | Planning slots, not preassigned n/100 numbers; all piece IDs and confirmed dates are blank. |

## Acceptance checks

```sh
python3 -m unittest discover -s tests -p test_release_packet.py -v
python3 -m unittest discover -s tests -p test_post_poem.py -v
node tools/verify_release_preview.cjs \
  --packet .post-poem-work/t03-first-release \
  --out .post-poem-work/t03-browser-check \
  --chrome /absolute/path/to/chromium
```

The browser verifier uses the available Playwright runtime. It binds a temporary server to `127.0.0.1`, blocks external browser requests, tests desktop and touch/phone-width emulation, opens the actual information panel and Journal view, records errors and requested image paths, and saves screenshots. It does not simulate the deployment host's HTTP headers. `_headers` is checked as an output file. Phone emulation is not a physical iPhone test; T04 owns that acceptance record.

Build the packet again to a second new directory and compare `preview/` file hashes. Generated observation timestamps and local output paths are not supposed to be identical; the proposed public bytes are. The regression test performs this comparison. The exact atlas bytes must reconstruct from only the selected page regions, including white padding, and image tiers copied from the source must match their source hashes. Text exclusion alone is insufficient.

Before any later posting operation, refresh the PR/code head and a database export with T01, hash the inputs, reconcile pending T02 source changes and T04 reader changes, rerun this inspection, and complete the [release-clearance contract](release-clearance-contract.md). T03's prepared artifacts are invalidated by changed input bytes. Do not use `--force` or `--accept-shared-scan` as substitutes for missing evidence or author clearance.

## Actual outstanding gates

1. Author confirmation of the first piece, pool and exact version; the preserved release collection is empty.
2. Author confirmation of the documented filed/registered workflow and actual filing/deposit evidence linked to the selected version. The preserved batches collection is empty. T03 neither files nor decides legal sufficiency.
3. Author review of the exact image exposure and downloaded font metadata. The font family/title are implemented as `ajp-scribbles`/`versforms`; metadata includes an author name and a handwriting-source description.
4. Author review of the retained information-panel text: empty scan provenance fields and the global “not yet checked by the author” sentence. Line-review completeness does not rewrite this wording automatically.
5. Confirm event categorization before automation consumes Site/social publication flags. Use the database-backed acceptance receipt and integrator handoff; no legal classification is inferred from the current booleans.
6. Physical-phone acceptance, accepted integrator revision, and a fresh complete export. These are separate from the bounded headless preview checks.

The old November 1 launch date is elapsed history. Proposal as of November 5: review this packet in the next author session; after all gates are satisfied, choose an explicit start date and repeat at seven-day intervals. No future day is a commitment or scheduled task. Keep the weekly cadence and existing-resource/no-spend constraint; a funding or filing-policy conflict remains a decision, not permission to bypass the gate.

## Rollback and recovery

**During this preparation:** there is no release state to roll back. Source `site/`, `studio/`, the exported records and `release/public.json` retain their pre-run hashes. Generated output lives in a separate directory. Preserve the packet/receipt as evidence; it can be regenerated from the recorded revision and inputs.

**If a later authorized public change must be withdrawn:** stop downstream scheduling, record the exact public commit and affected file hashes, and prepare a revert PR in the public repository. For a verified merge commit use `git revert -m 1 <merge-commit>`; for a squash or ordinary commit use `git revert <commit>`. Determine the actual merge method first. Remove the matching IDs and any `all_versions` entries from the private whitelist in a coordinated private PR so a subsequent build cannot restore them. Rebuild and inspect the replacement output for all remaining pieces, including images, spreads, atlases and caches. These are future instructions, not actions taken here.

Keep the exposure history: withdrawal does not erase an appearance or prove copies were recalled. Record a withdrawal event with the original event/URL and version references rather than deleting the original log. If a proposed schema cannot represent that event, stage it with the studio integrator before writing it. Restore a local test database from its pre-test export if needed; never replay test posting records into live D1.

No history rewrite, force push, live-state change, issue closure, filing or public deployment is part of this procedure's execution authority.
