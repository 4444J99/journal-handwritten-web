# Scan measurements — paper edge vs black bar (JHW #48, step 1)

Measured 2026-11-27 at main `faa3863d` with `tools/image_tiers.py`
(`paper_box`, two-pass border-darkness measurement) over all 123
`site/img/p/` masters. The exchange doc (issue #48) asserts black bars
exist and must be cropped to the paper; this report is the measurement
that assertion was never given before.

## Method

- Grayscale, downscaled to max dimension 500. A border row/column is
  "dark" when value < 60; a paper row/column is mostly bright even with
  ink, so the paper edge is the first row/column whose dark fraction
  drops below 0.5 and stays below for the next three rows/columns.
- Two passes: column profiles over the full height give left/right,
  then row profiles restricted to the paper's column range give
  top/bottom. One pass fails on diary25, where a vertical dark band
  (the desk left of the paper) makes every full-width row >50% dark.
- The measured box is checked against the paper box `j.json` already
  records in each page's `c` field: **0 mismatches across all 123
  pages** (1% tolerance). The measurement independently reproduces
  the recorded boxes; `c` stays the source of truth and is never edited.

## Findings

- **Black bars exist on 2 of 123 pages: diary25 and diary25a** (byte-identical
  scans). The left ~67% of the frame is a dark surface and the paper
  occupies the right ~33% (`c: [0.6719, 0.0016, 0.9994, 0.9644]`,
  measured left inset 1075px, bottom inset 42px). The handwriting is cut
  at the paper's left edge — the transcriber marked those line starts
  `[[?]]` in `B`. These two are the only genuine paper-crop case.
- **The other 121 pages are already tight to the paper**: median inset 0px
  on all four sides, max 0px. No crop is needed; the paper-crop step
  records the full-frame box for them.
- **Paper aspect: median 0.756; 70 pages taller than 4:5, 53 wider.** The
  tall-page case the exchange doc calls out is the norm, not the exception.
- **Strips (aspect > 2): 12** — diary14a, diary26, diary31, diary35a, diary37, diary37a, diary4, diary43, diary59, diary59a, diary60a, diary7.
- **Narrow pages (aspect < 0.5): 4** — diary18, diary19, diary25, diary25a.
- **Pages with no `x` line-box rows: 23** — diary21, diary25, diary25a, diary37, diary37a, diary39a, diary40, diary40a, diary41, diary41a, diary43, diary45, diary47, diary47a, diary48a, diary49a, diary50, diary50a, diary51, diary51a, diary59, diary59a, diary60a.
  Their covers fall back to the whole paper box (kit.py render_page rule);
  `B` carries line text, not geometry, so no opening-block box exists for them.
- **13 further pages have line boxes but none in block 0** (their block 0
  has no geometry). Their covers use the first block with geometry
  (lowest-numbered block with `x` rows), not the whole page.

## Consequence for the build

The paper-crop step records the measured box per page (full frame for 121,
the diary25 box for 2) in `images-crops.json` and derives one 4:5 cover
per page from the opening block's line boxes (or the whole paper box where
no line boxes exist). The 4:5 cover — not the paper crop — is the real
deliverable: the paper is already where the scans say it is.

## Per-page table

| page | master size | paper box (norm) | aspect | cover source |
| --- | --- | --- | --- | --- |
| diary1 | 1135x1600 | [0.0, 0.0, 1.0, 1.0] | 0.709 | opening-block (block 0) |
| diary10 | 1361x1381 | [0.0, 0.0, 1.0, 1.0] | 0.986 | opening-block (block 0) |
| diary10a | 1255x1391 | [0.0, 0.0, 1.0, 1.0] | 0.902 | opening-block (block 0) |
| diary11 | 1115x1600 | [0.0, 0.0, 1.0, 1.0] | 0.697 | opening-block (block 0) |
| diary11a | 1503x990 | [0.0, 0.0, 1.0, 1.0] | 1.518 | opening-block (block 0) |
| diary12 | 1474x1600 | [0.0, 0.0, 1.0, 1.0] | 0.921 | opening-block (block 0) |
| diary12a | 1425x1011 | [0.0, 0.0, 1.0, 1.0] | 1.409 | opening-block (block 0) |
| diary13 | 1325x1600 | [0.0, 0.0, 1.0, 1.0] | 0.828 | opening-block (block 0) |
| diary13a | 1105x1600 | [0.0, 0.0, 1.0, 1.0] | 0.691 | opening-block (block 0) |
| diary14 | 1190x1600 | [0.0, 0.0, 1.0, 1.0] | 0.744 | opening-block (block 0) |
| diary14a | 1468x409 | [0.0, 0.0, 1.0, 1.0] | 3.589 | opening-block (block 0) |
| diary15 | 885x1600 | [0.0, 0.0, 1.0, 1.0] | 0.553 | opening-block (block 0) |
| diary15a | 1030x1600 | [0.0, 0.0, 1.0, 1.0] | 0.644 | opening-block (block 0) |
| diary16 | 544x691 | [0.0, 0.0, 1.0, 1.0] | 0.787 | opening-block (block 0) |
| diary16a | 1249x1600 | [0.0, 0.0, 1.0, 1.0] | 0.781 | opening-block (block 0) |
| diary17 | 873x1591 | [0.0, 0.0, 1.0, 1.0] | 0.549 | opening-block (block 0) |
| diary17a | 984x1600 | [0.0, 0.0, 1.0, 1.0] | 0.615 | opening-block (block 0) |
| diary18 | 683x1600 | [0.0, 0.0, 1.0, 1.0] | 0.427 | opening-block (block 0) |
| diary18a | 873x1600 | [0.0, 0.0, 1.0, 1.0] | 0.546 | opening-block (block 0) |
| diary19 | 639x1600 | [0.0, 0.0, 1.0, 1.0] | 0.399 | opening-block (block 0) |
| diary19a | 819x1600 | [0.0, 0.0, 1.0, 1.0] | 0.512 | opening-block (block 0) |
| diary2 | 1313x1600 | [0.0, 0.0, 1.0, 1.0] | 0.821 | opening-block (block 0) |
| diary20 | 1103x1600 | [0.0, 0.0, 1.0, 1.0] | 0.689 | opening-block (block 0) |
| diary20a | 1095x1600 | [0.0, 0.0, 1.0, 1.0] | 0.684 | opening-block (block 0) |
| diary21 | 1131x1600 | [0.0, 0.0, 1.0, 1.0] | 0.707 | whole-paper |
| diary21a | 986x773 | [0.0, 0.0, 1.0, 1.0] | 1.276 | opening-block (block 0) |
| diary22 | 1485x886 | [0.0, 0.0, 1.0, 1.0] | 1.676 | opening-block (block 0) |
| diary22a | 990x1600 | [0.0, 0.0, 1.0, 1.0] | 0.619 | opening-block (block 1) |
| diary23 | 1463x1600 | [0.0, 0.0, 1.0, 1.0] | 0.914 | opening-block (block 2) |
| diary23a | 1441x1263 | [0.0, 0.0, 1.0, 1.0] | 1.141 | opening-block (block 0) |
| diary24 | 1477x1188 | [0.0, 0.0, 1.0, 1.0] | 1.243 | opening-block (block 0) |
| diary24a | 1444x1399 | [0.0, 0.0, 1.0, 1.0] | 1.032 | opening-block (block 0) |
| diary25 | 1600x1236 | [0.6719, 0.0, 1.0, 0.966] | 0.44 | whole-paper |
| diary25a | 1600x1236 | [0.6719, 0.0, 1.0, 0.966] | 0.44 | whole-paper |
| diary26 | 1400x588 | [0.0, 0.0, 1.0, 1.0] | 2.381 | opening-block (block 0) |
| diary26a | 1411x1499 | [0.0, 0.0, 1.0, 1.0] | 0.941 | opening-block (block 0) |
| diary27 | 1283x1600 | [0.0, 0.0, 1.0, 1.0] | 0.802 | opening-block (block 0) |
| diary27a | 1083x1600 | [0.0, 0.0, 1.0, 1.0] | 0.677 | opening-block (block 0) |
| diary28 | 1027x1600 | [0.0, 0.0, 1.0, 1.0] | 0.642 | opening-block (block 0) |
| diary28a | 1448x1161 | [0.0, 0.0, 1.0, 1.0] | 1.247 | opening-block (block 0) |
| diary29 | 1094x1600 | [0.0, 0.0, 1.0, 1.0] | 0.684 | opening-block (block 0) |
| diary29a | 1104x1600 | [0.0, 0.0, 1.0, 1.0] | 0.69 | opening-block (block 0) |
| diary2a | 1496x1166 | [0.0, 0.0, 1.0, 1.0] | 1.283 | opening-block (block 0) |
| diary3 | 1356x1600 | [0.0, 0.0, 1.0, 1.0] | 0.848 | opening-block (block 0) |
| diary30 | 1063x1600 | [0.0, 0.0, 1.0, 1.0] | 0.664 | opening-block (block 0) |
| diary30a | 1247x1600 | [0.0, 0.0, 1.0, 1.0] | 0.779 | opening-block (block 0) |
| diary31 | 1109x467 | [0.0, 0.0, 1.0, 1.0] | 2.375 | opening-block (block 0) |
| diary31a | 1061x1600 | [0.0, 0.0, 1.0, 1.0] | 0.663 | opening-block (block 0) |
| diary32 | 1371x1283 | [0.0, 0.0, 1.0, 1.0] | 1.069 | opening-block (block 0) |
| diary32a | 1368x1475 | [0.0, 0.0, 1.0, 1.0] | 0.927 | opening-block (block 0) |
| diary33 | 1201x1600 | [0.0, 0.0, 1.0, 1.0] | 0.751 | opening-block (block 0) |
| diary33a | 1209x1600 | [0.0, 0.0, 1.0, 1.0] | 0.756 | opening-block (block 1) |
| diary34 | 902x1600 | [0.0, 0.0, 1.0, 1.0] | 0.564 | opening-block (block 0) |
| diary34a | 1429x1431 | [0.0, 0.0, 1.0, 1.0] | 0.999 | opening-block (block 0) |
| diary35 | 1010x1600 | [0.0, 0.0, 1.0, 1.0] | 0.631 | opening-block (block 1) |
| diary35a | 1398x642 | [0.0, 0.0, 1.0, 1.0] | 2.178 | opening-block (block 0) |
| diary36 | 1307x1443 | [0.0, 0.0, 1.0, 1.0] | 0.906 | opening-block (block 1) |
| diary36a | 1339x1409 | [0.0, 0.0, 1.0, 1.0] | 0.95 | opening-block (block 0) |
| diary37 | 1411x388 | [0.0, 0.0, 1.0, 1.0] | 3.637 | whole-paper |
| diary37a | 959x147 | [0.0, 0.0, 1.0, 1.0] | 6.524 | whole-paper |
| diary38 | 1041x1600 | [0.0, 0.0, 1.0, 1.0] | 0.651 | opening-block (block 1) |
| diary38a | 1066x1600 | [0.0, 0.0, 1.0, 1.0] | 0.666 | opening-block (block 0) |
| diary39 | 921x1600 | [0.0, 0.0, 1.0, 1.0] | 0.576 | opening-block (block 0) |
| diary39a | 1072x1600 | [0.0, 0.0, 1.0, 1.0] | 0.67 | whole-paper |
| diary3a | 1449x1507 | [0.0, 0.0, 1.0, 1.0] | 0.962 | opening-block (block 0) |
| diary4 | 1459x669 | [0.0, 0.0, 1.0, 1.0] | 2.181 | opening-block (block 0) |
| diary40 | 1091x1600 | [0.0, 0.0, 1.0, 1.0] | 0.682 | whole-paper |
| diary40a | 1085x1600 | [0.0, 0.0, 1.0, 1.0] | 0.678 | whole-paper |
| diary41 | 1129x1600 | [0.0, 0.0, 1.0, 1.0] | 0.706 | whole-paper |
| diary41a | 1243x1600 | [0.0, 0.0, 1.0, 1.0] | 0.777 | whole-paper |
| diary42 | 1347x1083 | [0.0, 0.0, 1.0, 1.0] | 1.244 | opening-block (block 0) |
| diary42a | 1113x1600 | [0.0, 0.0, 1.0, 1.0] | 0.696 | opening-block (block 0) |
| diary43 | 1061x179 | [0.0, 0.0, 1.0, 1.0] | 5.927 | whole-paper |
| diary43a | 1205x1264 | [0.0, 0.0, 1.0, 1.0] | 0.953 | opening-block (block 0) |
| diary44 | 1320x1272 | [0.0, 0.0, 1.0, 1.0] | 1.038 | opening-block (block 0) |
| diary44a | 984x1600 | [0.0, 0.0, 1.0, 1.0] | 0.615 | opening-block (block 2) |
| diary45 | 981x1600 | [0.0, 0.0, 1.0, 1.0] | 0.613 | whole-paper |
| diary45a | 1000x1600 | [0.0, 0.0, 1.0, 1.0] | 0.625 | opening-block (block 6) |
| diary46 | 1034x1600 | [0.0, 0.0, 1.0, 1.0] | 0.646 | opening-block (block 0) |
| diary46a | 1032x1600 | [0.0, 0.0, 1.0, 1.0] | 0.645 | opening-block (block 0) |
| diary47 | 1022x1600 | [0.0, 0.0, 1.0, 1.0] | 0.639 | whole-paper |
| diary47a | 1055x1600 | [0.0, 0.0, 1.0, 1.0] | 0.659 | whole-paper |
| diary48 | 1344x1600 | [0.0, 0.0, 1.0, 1.0] | 0.84 | opening-block (block 0) |
| diary48a | 991x1600 | [0.0, 0.0, 1.0, 1.0] | 0.619 | whole-paper |
| diary49 | 1012x1600 | [0.0, 0.0, 1.0, 1.0] | 0.632 | opening-block (block 1) |
| diary49a | 1024x1600 | [0.0, 0.0, 1.0, 1.0] | 0.64 | whole-paper |
| diary4a | 1429x1216 | [0.0, 0.0, 1.0, 1.0] | 1.175 | opening-block (block 0) |
| diary5 | 1210x1600 | [0.0, 0.0, 1.0, 1.0] | 0.756 | opening-block (block 0) |
| diary50 | 1027x1600 | [0.0, 0.0, 1.0, 1.0] | 0.642 | whole-paper |
| diary50a | 1023x1600 | [0.0, 0.0, 1.0, 1.0] | 0.639 | whole-paper |
| diary51 | 1006x1600 | [0.0, 0.0, 1.0, 1.0] | 0.629 | whole-paper |
| diary51a | 997x1600 | [0.0, 0.0, 1.0, 1.0] | 0.623 | whole-paper |
| diary52 | 1015x1600 | [0.0, 0.0, 1.0, 1.0] | 0.634 | opening-block (block 5) |
| diary52a | 988x1600 | [0.0, 0.0, 1.0, 1.0] | 0.618 | opening-block (block 0) |
| diary53 | 1051x1600 | [0.0, 0.0, 1.0, 1.0] | 0.657 | opening-block (block 0) |
| diary53a | 1258x1600 | [0.0, 0.0, 1.0, 1.0] | 0.786 | opening-block (block 0) |
| diary54 | 1237x1600 | [0.0, 0.0, 1.0, 1.0] | 0.773 | opening-block (block 0) |
| diary54a | 1037x1600 | [0.0, 0.0, 1.0, 1.0] | 0.648 | opening-block (block 0) |
| diary55 | 1323x1600 | [0.0, 0.0, 1.0, 1.0] | 0.827 | opening-block (block 1) |
| diary55a | 1088x1600 | [0.0, 0.0, 1.0, 1.0] | 0.68 | opening-block (block 0) |
| diary56 | 1086x1600 | [0.0, 0.0, 1.0, 1.0] | 0.679 | opening-block (block 0) |
| diary56a | 1103x1600 | [0.0, 0.0, 1.0, 1.0] | 0.689 | opening-block (block 0) |
| diary57 | 1304x1600 | [0.0, 0.0, 1.0, 1.0] | 0.815 | opening-block (block 0) |
| diary57a | 1015x1600 | [0.0, 0.0, 1.0, 1.0] | 0.634 | opening-block (block 0) |
| diary58 | 950x1600 | [0.0, 0.0, 1.0, 1.0] | 0.594 | opening-block (block 0) |
| diary58a | 984x1600 | [0.0, 0.0, 1.0, 1.0] | 0.615 | opening-block (block 1) |
| diary59 | 1447x403 | [0.0, 0.0, 1.0, 1.0] | 3.591 | whole-paper |
| diary59a | 1333x358 | [0.0, 0.0, 1.0, 1.0] | 3.723 | whole-paper |
| diary5a | 1423x1474 | [0.0, 0.0, 1.0, 1.0] | 0.965 | opening-block (block 0) |
| diary60 | 1287x1537 | [0.0, 0.0, 1.0, 1.0] | 0.837 | opening-block (block 0) |
| diary60a | 1378x255 | [0.0, 0.0, 1.0, 1.0] | 5.404 | whole-paper |
| diary61 | 1298x1600 | [0.0, 0.0, 1.0, 1.0] | 0.811 | opening-block (block 0) |
| diary61a | 1020x1600 | [0.0, 0.0, 1.0, 1.0] | 0.637 | opening-block (block 0) |
| diary62 | 1236x1369 | [0.0, 0.0, 1.0, 1.0] | 0.903 | opening-block (block 1) |
| diary62a | 1310x1600 | [0.0, 0.0, 1.0, 1.0] | 0.819 | opening-block (block 0) |
| diary63 | 1039x1317 | [0.0, 0.0, 1.0, 1.0] | 0.789 | opening-block (block 0) |
| diary63a | 1048x1550 | [0.0, 0.0, 1.0, 1.0] | 0.676 | opening-block (block 0) |
| diary7 | 1340x622 | [0.0, 0.0, 1.0, 1.0] | 2.154 | opening-block (block 0) |
| diary7a | 1428x1359 | [0.0, 0.0, 1.0, 1.0] | 1.051 | opening-block (block 0) |
| diary8 | 1497x1365 | [0.0, 0.0, 1.0, 1.0] | 1.097 | opening-block (block 0) |
| diary8a | 1344x1588 | [0.0, 0.0, 1.0, 1.0] | 0.846 | opening-block (block 0) |
| diary9 | 1395x1600 | [0.0, 0.0, 1.0, 1.0] | 0.872 | opening-block (block 0) |
| diary9a | 1312x1315 | [0.0, 0.0, 1.0, 1.0] | 0.998 | opening-block (block 0) |
