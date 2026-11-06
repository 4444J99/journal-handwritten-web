# T07 media-production kit

One source package produces every T07 output: stills, carousel, Reel, 9:16
assembly and a private scan-based widget kit. The same code path runs for a
second piece without changes.

## Layout

```
production/
  README.md
  assets/                 byte-identical copies of the preserved scans + T06 avatar
  kit/
    kit.py                generator
    config/p001.json      primary candidate
    config/p004.json      second-piece substitution
    templates/            editable 4:5 and 9:16 templates
  tools/
    vision_ocr.swift      Apple Vision OCR helper
    recover_mockups.py    recovers the bundled design-canvas boards
    check_substitution.py second-piece check
  exports/
    p001/                 representative private exports + manifest + QA
    p004/                 second-piece demo
    substitution-check.json
  device/                 Photos/widget device-test record
  reference/              recovered mockups + target-journal research
  DISPOSITION.md          per-issue disposition
```

## Reproduce

```sh
python3 production/kit/kit.py --config production/kit/config/p001.json \
  --out /private/scratch/t07-run/p001
python3 production/kit/kit.py --config production/kit/config/p004.json \
  --out /private/scratch/t07-run/p004
python3 production/tools/check_substitution.py \
  --primary /private/scratch/t07-run/p001 --substitute /private/scratch/t07-run/p004 \
  --out /private/scratch/t07-run/substitution-check.json
python3 -m unittest discover -s tests -p test_media_kit.py -v
```

Use a writable private scratch path in place of `/private/scratch/t07-run`.
Output directories must be empty: each run produces a complete independent
package, and existing author or generated files are preserved. Python requires
Pillow; ffmpeg must be on `PATH` for motion. Vision OCR requires macOS with
`swiftc`. Unavailable Vision and `--no-ocr` are recorded as **skipped**, with a
reason; geometry still runs. `--no-motion` makes a still/widget package and does
not satisfy the full-motion substitution check.

## Outputs (p001)

- `4x5/` — three comparable cover treatments at 1080×1350:
  `cover-stack` (A1), `cover-page` (A2), `cover-line` (A3).
- `carousel/` — five slides, including a later version cropped to blocks 0–2
  only (the p126 neighbour in blocks 3–4 is excluded).
- `reel/` — 6 s silent 1080×1920 soft wipe between the two versions, no overlay
  copy, poster frame, and all 180 encoder-input PNG frames.
- `story/` — provisional 9 s 1080×1920 write-on plus background and photo slots,
  with `assembly-spec.json`, three source layers, and all 270 encoder-input PNG
  frames. Only recorded line boxes are revealed; missing geometry is listed.
- `widget/` — private scan-based tiles and a private zip, plus `README.md`.
- `qa/` — 390 px phone previews, contact sheet, `readability.json`.
- `manifest.json` / `MANIFEST.md` — hashes, dimensions, clearance state. JSON
  covers every output file, including the Markdown index, QA files, posters,
  layers, all encoder frames and the zip; only JSON's own self-hash is excluded.
  The zip also lists hashes of its internal members, which must match the loose
  widget files.

## Source and crop provenance

Declared source hashes and byte counts are checked before rendering. Wrong
source bytes, a version outside the selected piece, or blocks outside that
version stop the run. Raw input records are separate from each consumer asset's
`sources` selections: page, version, block ids, raw-image hash, and the exact
crop in normalized and original-image pixel coordinates.

Every p004 consumer crop selects only block 1 of diary3, including its page
cover and page widget. The full preserved scan remains unchanged. The p001
later-version slide selects diary62a blocks 0–2, bounded above the recorded p126
neighbour boxes in blocks 3–4. Its source chain names diary62a and the later
version. Reel frames name the primary source, later source, or both according
to the hold/wipe timing. Supplied identity bytes appear only in the outputs
that composite that identity. Widget crops fit inside the tile without a
second centre crop that would discard part of the selected writing.

These bounds prove exclusion of recorded neighbouring line boxes. They do not
resolve unknown geometry or author clearance for the shared scans.

## Phone-size readability

QA uses each image's own source page, crop dimensions and reviewed lines. It
reports the 8 px threshold for **measured** ink boxes at 390 px display width.
Whole-selection readability is `null` whenever any reviewed line lacks a
recorded box. In the current data, p001's primary version has 21 measured boxes
for 22 lines; its later diary62a version has 13 for 16 lines, with unknowns at
block/line pairs `[0,3]`, `[1,0]`, `[2,5]`. The p004 selection has nine boxes for
nine lines. No geometry is borrowed from another page or inferred for a
missing line.

Apple Vision OCR, when available, compares against that version's reviewed
text. A skipped OCR run is never a pass. The substitution checker verifies
complete byte coverage and faithful accounting of geometry unknowns; a pass
does not certify every line's legibility. Physical-device review remains
required (see `device/`).

## Clearance

Status is `awaiting-author-and-evidence`; `may_publish: false`. A green build,
a `filed`/`registered` string, `pool=series`, a Series label or `--force` is
not permission. Author clearance is `null` and filing evidence is `null`.
See `docs/releases/release-clearance-contract.md` (T03) and
`production/DISPOSITION.md`.

## Boundaries honoured

- No merge, deploy, publish, spend, account change, issue closure or external
  message.
- Original scans and author text preserved; copies are byte-identical.
- No generated creative or interpretive copy on any export.
- No fabricated recordings: the 9:16 photo and background layers are still
  stand-ins, documented as missing.
- T06 identity used as supplied; not regenerated or relabelled.
