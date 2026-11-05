# Data shape: site/data/j.json and the line-tile pipeline

Technical notes for the alive prototype. Read from `site/index.html` and `site/data/j.json`
(both read-only). Checked against page `diary1` / piece `p001` only. No poem text here.

## j.json top level

| key | content |
|---|---|
| `v` | schema version (2) |
| `pages` | 123 page records (below) |
| `groups` | list of lists of page ids that belong together (e.g. a page and the page whose spread it shares) |
| `atlas` | `[[2048,2112],[2048,2197]]`: pixel sizes of atlas sheet 0 and 1 |
| `pieces` | 126 piece records (below) |
| `prov` | provenance of the scans: source repo, commit, date, `verified` flag |

## pages[] record

Keys: `B, H, W, a, c, id, ih, iw, pl, sp, u, x`. For `diary1`: `iw=1135, ih=1600, W=617.8, H=870.7`.

- `id`: page id; the full-page image is `site/img/p/<id>.jpg` (RGB, `iw` x `ih`).
- `iw`, `ih`: pixel size of `img/p/<id>.jpg`. This is the frame of every box below.
- `W`, `H`: layout units for the canvas (same aspect as `iw:ih`, `H = ih * 0.5442` for this page).
- `c`: `[x0,y0,x1,y1]` normalised page crop (here `[0,0,1,1]`, the whole page).
- `sp`: spread info: `s` side (`right`), `cb` crop box in the 3300 x 2550 spread image, `f` spread file ref (null here), `k` source file name.
- `u`: list of free-text reading-uncertainty notes (not used).
- `pl`: ink colour override (null here; the page code falls back to `#2a2c33`).
- `a`: atlas slot `[atlasIdx, x, y, w, h]`; for `diary1` it is `[0,0,0,213,300]`.
- `B`: blocks (below).
- `x`: per-line boxes (below).

### Atlas images

`img/a/t0.jpg`, `t1.jpg`: colour thumbnail sheets (2048 x 2112 and 2048 x 2197); one page thumbnail per slot, 300 px tall
(`a[4] = 300`, `a[3] = round(iw * 300/ih) = 213`), placed at `a[1], a[2]`. `img/a/k0.jpg`, `k1.jpg`: same layout, greyscale
(`L`), with the paper and ruled lines removed (ink on white). `pages[].a` indexes them: sheet `a[0]`, slot origin `a[1..2]`,
slot size `a[3..4]`. `lineSrc()` in index.html reads a line from the k sheet at
`(a[1] + c0*a[3], a[2] + c1*a[4])` with `c` the line crop in page fractions (tier 0), or from `img/m/<id>.jpg` (426 x 600, `L`,
keyed; tier 1) or `img/i/<id>.jpg` (851 x 1200, `L`, keyed; tier 2).
**Atlas resolution is far too low for segmentation**: a text line is about 8 to 10 px tall in the sheet. The i and m tiers are the
same frame scaled by 0.75 and 0.375 and have the rules removed, but thin strokes break up in them (checked by eye).

### Best image to crop from

`img/p/diary1.jpg`: 1135 x 1600, RGB, the only full-resolution tier, the frame of all boxes. It still carries the ruled lines
(see Geometry), so ink has to be separated from the rules in code (`segment.py` does it).

### Line boxes: pages[].x

One row per line that has a box: `[blockIdx, lineIdx, x0, y0, x1, y1, f6, f7]`.

- Indices 2 to 5 are the box, **fractions of `iw` (x) and `ih` (y)** of `img/p/<id>.jpg` (`index.html` uses `e.slice(2,6)`;
  `rectsSVG` multiplies by `p.iw` and `p.ih`). Pixel box = `[x0*iw, y0*ih, x1*iw, y1*ih]`.
- `f6` is a y fraction inside the box that tracks the writing baseline; `f7` is a small height fraction whose median times `ih`
  is 23.7 px, matching measured letter height (x-height). Both are inferred from the data; `index.html` does not read them.
- The boxes are loose: neighbours overlap vertically, some run to the page edge (`x0 = 0`).
- Lookup in the page code is by the key `blockIdx + "-" + lineIdx`.

**Defect found (diary1, block 2):** block 2 has 4 lines and only 3 boxes. Keys `2-1` and `2-2` hold the boxes of the
third and fourth lines (checked by overlay: IoU of the ink box of line 3 with box `2-1` is 0.69; box `2-2` overlaps the
fourth line at 0.18 because it is wide). The second line of block 2 has no box, and the fourth has no key of its own.
So the page code gives line 2 the box of line 3, and so on. All other lines key correctly (IoU 0.61 to 0.98).

### Blocks: pages[].B

`{t, L, g, v}`:
- `t`: block type (0 body text here; the page code sizes types 1 and 3 as title and marginalia).
- `L`: list of line strings (inline markup is parsed by `parse()` for strike/insert nodes; the 22 lines of `p001` are plain).
  No empty strings: a blank line is never stored.
- `g`: `[pieceIdx, versionIdx, order]`; for `diary1` all six blocks are `[0,0,0..5]` (piece index 0 = `p001`, version 0).
- `v`: index into `pieces[g[0]].V` (the version record).

### Stanzas and blank lines

Stanza = block. Blank lines and stanza breaks are not represented in `L`. In the image each of the five breaks between the six
blocks is exactly one empty ruled row (measured: ruled rows used per block 3,4,4,4,3,4 with one unused row between blocks).
The data carries no relation between blocks beyond `g[2]`, the order.

## pieces[] record

`{id, V, st, top}`. `id` is `p001`...; `V` versions oldest to newest; `st` stack order (version indices, top first); `top`.
Each `V[i]` is `{P, d, id, s}`: `P = [[pageId, [blockIdx,...]], ...]` (which blocks of which pages), `d` (null here), `id`
(`p001-diary1-0`), `s` (source tag `j`). `p001`: `V[0]` = page `diary1` blocks 0 to 5 (22 lines, used);
`V[1]` = page `diary62a` (not used, carries a different piece).

## Geometry of diary1 (measured)

- Ruled lines: 28, evenly spaced (period 57.7 px), straight, tilted `dy/dx = +0.0218` (1.25 degrees, lower on the right).
  Handwriting follows the rules only loosely: lines drift against them and descenders of one line reach the next in the
  tighter stanzas (3 and 4).
- Page edge shadow: a dark sliver on the right edge (x = 1133 to 1135) must be ignored.
- x-height about 22 to 24 px; line pitch about 58 px.

## Segmentation results (proto/alive/segment.py, atoms-p001.json)

Method: shear to level the rules, Otsu threshold (171), strip rule pixels, 8-connected components, assign components to
rule rows by centroid, merge marks and fragments into glyphs, split words on gaps >= 1.25 x x-height.

- Ink rows found: 22 = transcription lines (stable across thresholds 110 to 190). Row-to-line order is the only text-to-line link.
- Line extents: ink x1 equals the author box x1 within 1.1 px on 19 of 22 lines; the three that differ are the two block-2
  lines hit by the key shift and one line whose descender tail runs 38 px past its author box. Line boxes are clamped to the page.
- Word boxes: 86 boxes against 90 whitespace tokens. Box count equals token count on 19 of 22 lines; one of those (a line in
  stanza 3) was found wrong by eye (boxes hold shifted ink) and withdrawn: 18 of 22 lines carry text. The gap rule and threshold
  were picked on these 22 lines, so this rate is optimistic.
- Glyph boxes (ink-component groups): 301 against 340 letters; count equals letters on 4 of 22 lines. Letters are spaced widely
  and some join, so a glyph is not a letter. Letter text is attached only on words whose glyph count equals the letter count in a
  word-aligned line: 112 of 340 letters (33 percent).
- Known flaws: some word crops in stanzas 3 and 4 carry ink from a neighbouring line's descenders; punctuation tokens that
  touch a word (a dash, a question mark) merge into the word box, which leaves three lines unaligned (a fourth is the
  withdrawn line above).
