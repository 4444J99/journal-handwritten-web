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
rule rows by centroid (this only decides which rule rows carry text: 22 of 28), **partition the ink between adjacent lines
with seams** (below), merge marks and fragments into glyphs, split words on gaps >= 1.25 x x-height.

### The seam partition

Defect: adjacent lines overlap vertically (a descender of line N touches an ascender of line N+1), so 8-connected components
merge across rows and a centroid hands whole strokes to the wrong line; line boxes then contain the neighbour's ink (the
boxes themselves, not just the crop, so scaling or un-clipping a crop cannot fix it).

- One seam per adjacent text-line pair (21), in the sheared frame: one boundary row per column, rows above it belong to the
  upper line, rows from it down to the lower line. Found by dynamic programming over the ink mask. Cost of a seam = number
  of 8-neighbour ink-ink adjacencies it separates (vertical at a column, horizontal and diagonal between neighbouring
  columns) + 0.05 per px of row change between neighbouring columns + 0.002 per px away from the middle of the band.
  The row may change by at most 6 px between neighbouring columns.
- Band of candidate rows: from rule + 1 (the median measured body bottom) to rule + 1.6 x-heights (37.9 px, just above the
  deepest single-line descender measured, 35.8 px). Across an empty ruled row (a stanza break) the band is widened up to
  the tallest measured ascender (53.7 px) above the next rule, and centred in the corridor.
- Every ink pixel gets exactly one owner (asserted: 104452 ink pixels before, 104452 owned after; seams strictly ordered).
  Components are relabelled inside each line, then glyph and word steps run per line as before. Rule residue lying on any
  rule (also an empty one) is dropped, because the partition hands a line the stubs on the empty rule above or below it.
- Output per line: `region` (closed polygon in page pixels, between the two seams; page y = Y - pad + slope * x; vertices at
  pixel-column centres, collinear runs merged, clamped to the page; line 0 starts at the page top, line 21 ends at the page
  bottom), `ink_px` (owned ink pixels), and `box`, word boxes and glyph boxes computed from the owned ink.
  `meta.partition` records the method, parameters, bands, per-line ink, cut counts and the before/after table
  (`before_after.per_line`: box and counts under the centroid rule and under the seams).
  A page pixel belongs to a region when its centre has top <= y < bottom. Checked on the stored file: 0 of 1,816,000 page
  pixels are claimed by two regions, 0 by none; 104450 of 104452 ink pixels (sheared to page, rounded) fall in the polygon
  of their owner (2 do not).
- Author override as data, not code: `seam-waypoints-diary1.json` (`waypoints: [{pair, points, tol}]`, page pixels). On its x
  range the seam is forced to stay within `tol` of the polyline; nothing else changes. The list is empty in this build.
  The mechanism was exercised once on a synthetic polyline in scratch (seam moved as asked, other pairs unchanged, ink
  conserved); no waypoint was traced.

Measured, before (centroid rule) and after (seams), same 22 lines:

| quantity | before | after |
|---|---|---|
| ink rows / lines | 22 | 22 |
| ink pixels owned in total | 104452 | 104452 |
| line pairs whose regions overlap | not defined (no regions) | 0 |
| line pairs whose boxes overlap in y (page frame) | 10 | 10 (12-13: 57 to 27 px, 13-14: 32 to 25, 16-17: 47 to 39, others unchanged) |
| components of the page labelling whose pixels land on two lines | not defined | 5 (of 6 that touch the x-height zone of two rule rows), cut at 5 sites, 47 separated ink adjacencies |
| line 13 box (x0, y0, x1, y1) | 57, 911, 990, 1017 (106 px tall) | 57, 948, 990, 1037 (89 px tall) |
| line 13 first word box height | 97 px | 60 px |
| boxes taller than 80 px (page frame) | lines 9, 13, 14, 15, 17, 19 | lines 9, 12, 13, 15, 16, 19 (the 1.25 degree tilt adds about 22 px of the height) |
| ink of another line inside word boxes | 5853 px (diagnosis run) | 1380 px (re-measured) |
| glyph boxes (non-mark) | 301 | 306 |
| lines whose word-box count equals the token count | 19 | 19 (same lines) |

All numbers are in-sample: the seam parameters (band depth, ascender height, step, straightness, centring) were fixed after
looking at these same 22 lines, the band depth and the ascender height are themselves measured on this page, and no held-out
page exists. The word-box count did not improve (19 of 22 before and after): the partition changes which ink a box holds, not
how many boxes there are. The gain in letters that sit in count-equal words (112 to 116 of 340) follows from the changed
glyph counts and is not a validated improvement.

What the seam gets wrong: it cuts a stroke where the cut is cheapest, not where the pen left the line. On the pair (line 12,
line 13) it cuts three descender loops of line 12 at the neck (x about 173, 765, 956 in page pixels) and hands about 1500 ink
pixels (1.5 percent of the page ink) to line 13; the loops show above and inside line 13's first and fourth word boxes. The
two other cut sites that matter (x about 572 between lines 13 and 14, x about 815 between lines 16 and 17) cut at a real contact.
Tried and rejected in the diagnosis: deeper band with a depth prior (fixes the loops, cuts the tops of line 13's round letters),
a pin over a whole component. Stroke direction at the crossings was not checked, only the greyscale at 5x by eye.

### Line 13

Word-box count equals token count (4 for 4) but, re-checked by eye on the new partition at full resolution, the first word
box holds a descender loop of line 12 over its round letters and the fourth holds two more, and the upper bowl of
the last letter group is split with line 12. Its text stays withdrawn (`words_alignment` null, no `text` on its words). It is
restored only when the author traces waypoints for that pair and the word crops pass the same eye review. Lines 11, 12 and
21 (2 boxes for 3 tokens, 6 for 7, 6 for 8) remain unaligned; the seam does not help them.

### Earlier results (unchanged by the partition)

- Ink rows found: 22 = transcription lines (stable across thresholds 110 to 190). Row-to-line order is the only text-to-line link.
- Line extents: ink x1 equals the author box x1 within 1.1 px on 19 of 22 lines; the three that differ are the two block-2
  lines hit by the key shift and one line whose descender tail runs 38 px past its author box. Line boxes are clamped to the page.
- Word boxes: 86 boxes against 90 whitespace tokens. Box count equals token count on 19 of 22 lines; one of those (line 13)
  was found wrong by eye and withdrawn: 18 of 22 lines carry text. The gap rule and threshold were picked on these 22 lines,
  so this rate is optimistic.
- Glyph boxes (ink-component groups): 306 against 340 letters; count equals letters on 4 of 22 lines. Letters are spaced widely
  and some join, so a glyph is not a letter. Letter text is attached only on words whose glyph count equals the letter count in a
  word-aligned line: 116 of 340 letters (34 percent).
- Known flaws: punctuation tokens that touch a word (a dash, a question mark) merge into the word box, which leaves three lines
  unaligned (a fourth is the withdrawn line above); the seam sites listed above.
