# Editable templates

Two browser-openable templates mirror the generator's compositions:

- `frame-4x5.html` — the 4:5 frame with the three cover treatments used for #45
  and #67: **A1 stack** (page card + blurred scan + identity chip), **A2 page
  alone**, **A3 one line**.
- `story-9x16.html` — the 9:16 assembly with the recorded-ink reveal, the
  background loop slot and the photo loop slot.

They are editing aids, not a second renderer. The authoritative exports come
from `production/kit/kit.py`, which crops against the line boxes in
`site/data/j.json` and records hashes. The CSS crops here are approximate.

## Swap the source

1. Copy the chosen scan into `production/assets/` and update `--scan`, `--page`
   or `--background` in the template.
2. Set `--focus-x` / `--focus-y` / `--zoom` for the crop. For the exact
   generator crop, use the page/version/block ids in the kit config.
3. For a line crop, prefer the pre-cropped image from
   `production/exports/<piece>/4x5/cover-line.jpg` and place it in
   `.treatment-line .crop`.
4. Set `--frame-w: 1080px` before export.

## Rules

- **No generated copy.** Author-supplied text only. The templates contain no
  overlay text; the labels on this page are editing notes and are outside the
  frame.
- The avatar is the T06 supplied image, currently `supplied/unapproved`
  (D13 unresolved). Do not regenerate or relabel it.
- The 9:16 photo and background slots are **empty**. Do not fill them with
  generated footage; the finished sample needs the author's Live Photo/video.
- The write-on is a mask over recorded scan ink. A reconstructed stroke
  animation is a different artistic treatment and needs the author's decision.
- Nothing here is cleared. See `production/README.md` and the export manifest.
