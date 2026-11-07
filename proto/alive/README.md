# alive prototype (standalone)

Technical notes. A separate prototype: it does not replace anything in `site/` or `studio/` (both are read, never
edited) and it is not wired into the real piece. Private: it reads the author's private archive. Serve it on
127.0.0.1 only; never copy it, its data files or any build of it to a public host or the public repository.

Vanilla JS and Canvas 2D. No framework, no CDN, no network beyond same-origin. The page has no `<title>`, no alt text
and no labels. Nothing is written on screen except, on demand, the unit names (see "Hidden selector").

## Run

    node proto/alive/serve.mjs --port 8765        # prints http://127.0.0.1:8765/ ; --port 0 picks a free port
    open "http://127.0.0.1:8765/?city=p001"

`serve.mjs` binds 127.0.0.1, answers GET/HEAD only and serves a whitelist: `index.html`, `alive.js`, `atoms-p001.json`,
`rules-diary1.json`, `city-all58.json` (all in this folder), `site/img/p/diary1.jpg` and `site/img/i/<page>.jpg`.
Anything else is a 404; `..`, encoded separators, NUL bytes and symlinks leaving the repository are refused (400/403).
Unlike the brief's "site/data" wording it does not serve `site/data/j.json` or `studio/data/review.json`: the page does not
need them (the boxes it uses were extracted into the two JSON files below).

`python3 -B proto/alive/build_atoms.py --out proto/alive/atoms-p001.json` regenerates the p001 atoms (segmentation, seam
partition, regions); `atoms-p001.json` is never edited by hand. Author seam constraints, if any, are data in
`seam-waypoints-diary1.json` (none yet). `python3 proto/alive/build_data.py` regenerates `rules-diary1.json` and `city-all58.json` (reads `site/` and `studio/`,
writes only those two files; no line text is written to them).

## Query parameters

| param | values | effect |
|---|---|---|
| `city` | `p001` (default), `all58` | `p001`: one building in the local prototype. `all58`: the 58 complete pieces (group g==1 in `studio/data/review.json`), in journal page order. Private, local only. |
| `view` | `architecture` (default), `spiral`, `reading` | starting view. `reading` always shows p001. |
| `unit` | architecture: `poem stanza line word glyph`; spiral: `line page` | pins the unit (architecture) or sets the spiral mode. |
| `seed` | integer (default 1) | seed of the reading animation's PRNG |
| `t` | seconds | freezes the reading animation at simulated time `t`, simulated from 0 in fixed 1/30 s steps; the frame is identical on every load |

## Test hooks: `window.__alive`

`ready` (true once every piece's atlas is built; `document.body.dataset.ready` is set too), `setView(v)`,
`setUnit(u|null)`, `setSpiralUnit('line'|'page')`, `setTime(t)` (freezes and re-simulates from 0), `state()`, `sourcesUsed()`,
plus helpers used by the verifier: `spriteGeoms()`, `regionsRead()`, `allowedBoxes()`, `zoomToFloorPx(px)`, `setCamera(x,y,z)`,
`focus(id)`, `fit()`, `buildings()`, `tap(x,y)`, `render()`, `atlasLeak()` (per p001 line: atlas pixels with non-zero alpha
outside the line's region, which must be 0, and inside it) and `lineRegions()` (the region polygons as loaded).

- `state()` returns `{view, city, pinned, unit, zoom, floorPx, cam, selectorOpen, time, frozen, reduced, animating, frames,
  dark, sprites:[{piece:'p001', source:'line'|'word'|'glyph', blockId, lineIndex}], spriteCount, spriteSources:{line,word,glyph}, keepOut,
  viewport, pieces, readyPieces, failed}`. `unit` is the effective unit (the pinned one, else the zoom-driven one, clamped to
  what the nearest building has). `frames` counts requestAnimationFrame callbacks.
- `sourcesUsed()` lists the distinct line ids (`diary1-<block>-<line>`) the live sprites were cut from.
- `spriteGeoms()` gives, per live sprite, its crop box in page pixels, the box of the line it belongs to and its rotated
  screen bounding box, so a verifier can check both containment and the keep-out margin.
- `regionsRead()` lists every rectangle that was ever read from a page image.

## Data sources

- **p001**: `atoms-p001.json` (`build_atoms.py` output): 22 line boxes and 22 line `region` polygons, 86 word boxes, 306 glyph boxes,
  marks, 6 stanzas, poem box;
  pixels from `site/img/p/diary1.jpg` (1135x1600). Only V[0] of p001 (page `diary1`). The page holds nothing else.
- **all58**: `city-all58.json`, from `studio/data/review.json` (author review boxes) with `versions[0]` of each piece, boxes
  clipped so that none intersects a box of another item on the same page. Pixels from `site/img/i/<page>.jpg` (851x1200,
  the keyed tier: rules already removed, 0.75 of the page frame). p001 inside all58 uses the atoms boxes, not review.json,
  because review.json has the same block-2 key shift as j.json (see DATA.md).
- Ink treatment (all JS, in the page): luminance to alpha (smoothstep 236..95), tinted with the theme ink. p001 additionally
  has the ruled lines removed (`rules-diary1.json`: slope, pad and rule centres from `segment.py`; the spike's rule:
  clear +-2.5 px around each rule unless there is ink 5 px above or below; samples outside the box count as ink, so nothing
  is removed near a box edge); each line crop is masked to its own glyph and mark boxes (+2 px) and then to the line's
  `region` polygon (below). The `i` tier needs no rule removal.
- **Seam regions (p001).** Adjacent handwritten lines overlap vertically, so a line's rectangle holds strokes of its
  neighbours. `segment.py` therefore partitions the ink of the page: one seam per adjacent line pair (a min-cost path, one
  boundary row per column), every ink pixel owned by exactly one line. `atoms-p001.json` stores per line the polygon between
  its two seams in page pixels (`region`). `processLine()` keeps an atlas pixel only if its centre lies inside the polygon
  (even-odd crossings of the vertical through the pixel-column centre, half-open on y), so every crop is restricted to its assigned region: line, word, glyph, mark, reading sprites and spiral tiles are all read
  from that atlas. Assignment is geometric; it does not establish which handwritten line a crossing stroke belongs to. The polygon only restricts further; the rule-4 rectangle guard below is unchanged. Regions do not overlap by
  construction (seams strictly ordered); line rectangles still do. `window.__alive.atlasLeak()` reports 0 pixels outside.
  What the seam does not guarantee: it separates ink, it does not decide whose stroke a crossing stroke is. Three descender
  loops of one line (the line above line 13) are cut at the neck and land on line 13 (see DATA.md).
- The handwriting font is never used. Every picture on screen is a crop of the scans. No text is generated.

## Rule 4 mechanism

Every read of a page image goes through `readRegion(page, rect)`, which throws unless the rectangle is inside a registered
line box (tolerance 1.5 px for tier rounding). Registered boxes: p001's 22 atoms line boxes, and in all58 each piece's own
clipped line boxes. The atlas holds only those line rectangles. Word, glyph and mark crops are sub-rectangles of a line
rectangle. Reading sprites are drawn only from p001's atlas. `regionsRead()` is the audit log (the verifier checks all 22
reads against the atoms boxes in p001, and every read in all58 against `city-all58.json`).

## Views

**A. architecture** (`view=architecture`). Each poem is a building standing on a common ground line. Every line is a floor
64 world units high and as wide as the line box is wide (a page pixel is a world unit), centred on the building axis; the first
line is the top floor, the last the base floor. A stanza break is a 34 unit setback with a ledge. Unboxed lines are omitted
(never replaced by stand-in pixels). A skyline is the buildings in a row.
A crop may overflow its floor, top and bottom, by half of the excess of the tallest line box over the floor (p001: 92 px box,
so 14 units; capped at 16; the 57 other pieces keep 8), which avoids truncation by the floor window for the p001 boxes. The crop holds only its assigned region
ink; the documented seam-ownership errors can still place neighbouring descender strokes in that region. Floors are drawn in three passes (fills, crops, outlines) so that an overflow is not
painted over by the next floor's fill. The stanza unit uses the same overflow for p001 (it was 0). Scale-to-fit was not used:
fitting the six tall lines (box heights 84 to 92 px) into the 80 unit window would shrink them by up to 13 percent (30 percent into the bare 64 unit floor) against the other lines.
Units, chosen by the on-screen height of one floor (`floorPx`): `poem` < 4 px, `stanza` < 10, `line` < 48, `word` < 110,
`glyph` above. Drawing per unit: poem = one solid silhouette (floors and setbacks filled) with the line crops in it; stanza =
each stanza a solid slab (floors contiguous) with an outline; line = each floor outlined, ledges at setbacks; word = word
crops as windows with gaps on a wall-coloured floor; glyph = glyph and mark crops as bricks. A building that lacks a finer unit
is drawn at its finest.
Available units: city=p001: poem, stanza, line, word, glyph (max zoom: floor 360 px). city=all58: poem, stanza, line only
(max zoom: floor 100 px); there are no word or glyph boxes for the other 57 pieces, so pinning `word` or `glyph` there clamps to
`line`. `word-part` is not shipped (the spike judged it not viable).
Input: wheel / pinch zoom around the pointer, drag pans. Tap on p001's building opens READING. Tap on another building (all58)
zooms to it (no reading content). Pushing the zoom further after the clamp at the finest unit, on p001, also opens READING
(about 1.6x of extra zoom accumulated at the clamp); this choice avoids a collision with the glyph level being the deepest zoom.

**B. spiral** (`view=spiral`, key `b`, or a quick double tap on empty space from A). The same crops along an Archimedean
spiral in notebook (page) order, either lines (default) or pages. A line follows the tangent; a page is a tile (sheet colour
plus the piece's own line crops at their page positions, nothing else) kept upright. In city=p001 there is one page, so pages
mode shows one tile. This is a re-implementation for the demo; it is not the real engine's spiral. Tap an item: p001 opens
READING; another piece goes to its building in A.

**C. reading** (`view=reading`). p001's 22 line crops at their native positions in the poem box, in a clear column (sheet
coloured panel, nothing animates behind it) centred on the page; column width min(44% of the width, 640 px) (80% on narrow
screens), fitted to 84% of the height. Soft keep-out: the column plus a margin of max(22 px, 4% of the short side); a sprite
is placed only if its rotated bounding box is clear of it (a sprite that does not fit is shrunk by 0.8 up to 6 times, else
another point is tried).
Animation (dead space only): ghost copies of p001's own lines (18%), words (52%) and glyphs/marks (30%); random position,
rotation (70% within about +-0.8 rad, 30% anywhere), scale and alpha 0.12 to 0.55; lifetime 5 to 11 s with a 0.7 s fade-in and a
fade-out over the last 45%; `multiply` on light, `screen` on dark; newer sprites are drawn over older ones. Dynamics: empty
paper, ramp (smoothstep) to a target of 400 live sprites over 12 s, then churn at that density (spawn replaces expiry; at most
3 spawns per 1/30 s step). Simulation uses a fixed 1/30 s step driven by `dt` (clamped to 0.1 s, so a hidden tab resumes
without a jump); it pauses while `document.hidden`. `prefers-reduced-motion: reduce` renders one static frame (simulated to
14 s) and never animates. Measured on the canvas (seed 7, 1280x800, light and dark): the mean luminance moves by at most 0.04 of 255 per 1/30 s step
and at most 0.3 over 1/3 s in the t=10..11.5 s window, and by at most about 1.1 between samples 0.5 s apart over t=0..30 s
(the ramp); total drift from empty to dense is about 12 of 255 (light) and 13 of 255 (dark). No strobing.
Escape or a tap on dead space returns to the previous view; a tap on the column does nothing.

Only p001 has reading content in this prototype. Other buildings never open READING.

## Hidden selector

Hidden until a tap on empty space, a tap on the invisible 56x56 px zone in the bottom-left corner, or the `s` key. It shows the
unit names as plain small text and nothing else (architecture: poem, stanza, line, word, glyph; spiral: line, page; names that
the city does not have are dimmed). Tapping a name pins it. A second tap on empty space, Escape or `s` hides it and, in A,
returns to zoom-driven. In B the choice of line/page persists. Not shown in READING.
Keys: `s` selector, `a` architecture, `b` spiral, `Enter` open READING, `Escape` back/close, `+`/`-` zoom.

## Limits (checked or not, see the report)

- Word crops in p001 no longer carry a neighbouring line's ink across a seam, but where the seam cuts a stroke the wrong way
  the stroke sits on the wrong line: 3 sites on the pair (line 12, line 13) hold about 1500 ink pixels of descender loops
  that belong to line 12 and are owned by line 13 (the first and the fourth word crop of line 13 show them). Word text is
  never used. Glyph crops are ink-component groups, not letters. `atoms-p001.json` still contains the spike's transcription text; this
  page never reads it.
- all58 crops come from loose author boxes (clipped against other items' boxes) on the 0.75 tier: strokes are thinner or broken
  in places, rule stubs show at box edges that touch the page margin, and lines of other items that have no box cannot be
  excluded. 142 of the 1047 lines of the 58 pieces have no box and are omitted from their buildings. Pieces other than p001
  may have the same block key shift as diary1 block 2 (review boxes are used as authored); not audited.
- Pixel noise across theme switches: after repeated canvas read-backs, a re-render of the same architecture state (p001, fit view)
  differs from the earlier frames by 7419 of 4096000 channel values (largest difference 23 levels; 147 values before the floors
  were drawn in three passes). Frames drawn through the normal path (boot, theme switches) were identical to each other; only a
  frame drawn by an explicit `render()` after several read-backs differed. Suspected cause, not established: a different
  rasteriser path after the read-backs. Reading-view frames are pixel-identical across loads (SHA-256 check).
- Version 0 of each piece only.
- Reading is not scrollable: the column is fitted to the viewport.
