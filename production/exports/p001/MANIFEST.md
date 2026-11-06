# p001 media kit — private manifest

Generated: 2026-11-06T13:39:00+00:00  
Source revision: `c32f8b143635fff8def35c478b7610c0934639b6`  
Kit: `t07-media-kit-v1`  
Candidate: `p001` / `p001-diary1-0` / page `diary1`  
Pool: unsorted; no Series/Reserve/Archive decision  

**Status: awaiting author and evidence; `may_publish: false`.** This is a private kit. A green build or a Series label is not permission to publish.

## Assets

| asset | role | dimensions | bytes | sha256 | clearance |
|---|---|---|---|---|---|
| `4x5/cover-stack.jpg` | still | 1080×1350 | 234858 | `146d53f8e8f0e441…` | private-preview; awaiting author clearance; may_publish=false |
| `4x5/cover-page.jpg` | still | 1080×1350 | 233347 | `f93adbc27d67c245…` | private-preview; awaiting author clearance; may_publish=false |
| `4x5/cover-line.jpg` | still | 1080×1350 | 64538 | `80d28f2469802524…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-01-cover.jpg` | carousel | 1080×1350 | 234858 | `146d53f8e8f0e441…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-02-page.jpg` | carousel | 1080×1350 | 233347 | `f93adbc27d67c245…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-03-line.jpg` | carousel | 1080×1350 | 64538 | `80d28f2469802524…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-04-detail.jpg` | carousel | 1080×1350 | 76838 | `2ce7723463693267…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-05-version.jpg` | carousel | 1080×1350 | 216001 | `ca459d0ceeb04604…` | private-preview; awaiting author clearance; may_publish=false |
| `reel/p001-version-reel-1080x1920.mp4` | reel | 1080×1920 | 297198 | `f0f0b9bfea87dff5…` | private-preview; scan-derived; no audio; awaiting author clearance; may_publish=false |
| `reel/poster-1080x1920.jpg` | reel-poster | 1080×1920 | 88321 | `c3fb1e5b7609b524…` | private-preview; scan-derived; no audio; awaiting author clearance; may_publish=false |
| `story/p001-story-assembly-provisional-1080x1920.mp4` | story | 1080×1920 | 651110 | `d6e6845800d047b1…` | private-preview; scan-derived; no audio; awaiting author clearance; may_publish=false |
| `story/poster-1080x1920.jpg` | story-poster | 1080×1920 | 81152 | `24e88f92f5e66467…` | private-preview; scan-derived; no audio; awaiting author clearance; may_publish=false |
| `widget/tiles/2x1/opening-line.jpg` | widget-tile | 1600×760 | 115535 | `4476ed7ae8846beb…` | private test tile; not a public download; awaiting author clearance |
| `widget/tiles/2x1/detail-line.jpg` | widget-tile | 1600×760 | 149192 | `355c3bf05a5f27a8…` | private test tile; not a public download; awaiting author clearance |
| `widget/tiles/1x1/detail.jpg` | widget-tile | 1080×1080 | 104323 | `b1fdebe655e17f47…` | private test tile; not a public download; awaiting author clearance |
| `widget/tiles/1x1/opening.jpg` | widget-tile | 1080×1080 | 86212 | `bce23395a13e97b9…` | private test tile; not a public download; awaiting author clearance |
| `widget/tiles/2x2/page.jpg` | widget-tile | 1080×1080 | 175657 | `067eab93f227c653…` | private test tile; not a public download; awaiting author clearance |
| `widget/tiles/wide/opening.jpg` | widget-tile | 1600×760 | 89257 | `f090603bb5c83b7d…` | private test tile; not a public download; awaiting author clearance |
| `widget/p001-widget-kit-private.zip` | downloadable-kit | — | 676774 | `a1c0c6c8c26bd5f4…` | private zip; no public distribution; awaiting author clearance |

## Clearance

- schema: `versforms.release-clearance.v1`
- status: `awaiting-author-and-evidence`
- author clearance: `null`
- filing evidence: `null`
- shared scan: Unresolved. The later-version comparison crops diary62a to blocks 0-2 only, excluding the p126 neighbour in blocks 3-4; that crop is not a manuscript-wide exclusion proof and no author ruling exists.
- complete technical exclusion: `false` (T03's 13 withheld page ids and PAL/HF metadata are outside this kit's scope)
- may publish: `false`

## QA

- PIL ink-box geometry at a 390 px display width, plus Apple Vision OCR on the 390 px preview. Geometry is a proxy; physical-device review is still required.

| target | lines | min ink px @390 | median ink px @390 | geometry readable | OCR word recall |
|---|---|---|---|---|---|
| `cover-page` | 21 | 14.37 | 19.38 | yes | 0.674 |
| `cover-line` | 3 | 25.52 | 25.6 | yes | 0.875 |
| `cover-stack` | 21 | 13.6 | 18.34 | yes | 0.547 |
| `carousel-04-detail` | 3 | 24.7 | 24.88 | yes | 0.938 |
| `carousel-05-version` | 10 | 16.53 | 20.59 | yes | 0.471 |

## Missing

- Author clearance naming this exact output manifest and its limits.
- Series/Reserve/Archive decision for p001 and for the p126 neighbour.
- Author ruling on shared-scan exposure for diary62a blocks 3-4.
- Original Live Photo / video clips for the 9:16 photo layer (3 s loop) and background layer (4.5 s loop); current layers are still stand-ins.
- T06 D13 identity approval, or the original avatar assets if v3 is not the release identity.
- Physical iPhone Photos-widget test: album picker, render, shuffle, and shared-album behaviour. No iPhone or iOS Simulator is available in this environment.
- Target-journal treatment of Stories (permanent grid/Highlight/expiry) and whether expiry preserves any Reserve status; not yet confirmed for the selected journal.
- GRUW / filing evidence only if a filing claim is made; none is used here.

## Reproduction

```sh
python3 production/kit/kit.py --config production/kit/config/p001.json
```

The manifest is the authority for hashes and clearance state. Re-running after a source, crop, review, identity or clearance change invalidates this output.
