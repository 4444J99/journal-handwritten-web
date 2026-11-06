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
python3 -m venv /Volumes/Archive4T/Runtime/development/tmp/opencode/venv-t07
/Volumes/Archive4T/Runtime/development/tmp/opencode/venv-t07/bin/pip install Pillow
/Volumes/Archive4T/Runtime/development/tmp/opencode/venv-t07/bin/python production/kit/kit.py \
  --config production/kit/config/p001.json
/Volumes/Archive4T/Runtime/development/tmp/opencode/venv-t07/bin/python production/kit/kit.py \
  --config production/kit/config/p004.json
python3 production/tools/check_substitution.py
```

ffmpeg must be on `PATH` (motion step). Vision OCR requires macOS with
`swiftc`; if it is unavailable, geometry still runs and `--no-ocr` skips OCR.

## Outputs (p001)

- `4x5/` — three comparable cover treatments at 1080×1350:
  `cover-stack` (A1), `cover-page` (A2), `cover-line` (A3).
- `carousel/` — five slides, including a later version cropped to blocks 0–2
  only (the p126 neighbour in blocks 3–4 is excluded).
- `reel/` — 6 s silent 1080×1920 soft wipe between the two versions, no overlay
  copy, poster frame.
- `story/` — provisional 9 s 1080×1920 write-on plus background and photo slots,
  with `assembly-spec.json`.
- `widget/` — private scan-based tiles and a private zip, plus `README.md`.
- `qa/` — 390 px phone previews, contact sheet, `readability.json`.
- `manifest.json` / `MANIFEST.md` — hashes, dimensions, clearance state.

## Phone-size readability

Every measured target has an ink box of at least 8 px at a 390 px display width
(see `qa/readability.json`). Apple Vision OCR recall is reported as a lower
bound; cursive and faint passages under-read. Geometry is the primary measure;
physical-device review is still required (see `device/`).

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
