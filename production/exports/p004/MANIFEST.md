# p004 media kit — private manifest

Generated: 2026-11-06T13:39:35+00:00  
Source revision: `c32f8b143635fff8def35c478b7610c0934639b6`  
Kit: `t07-media-kit-v1`  
Candidate: `p004` / `p004-diary3-1` / page `diary3`  
Pool: unsorted; no Series/Reserve/Archive decision  

**Status: awaiting author and evidence; `may_publish: false`.** This is a private kit. A green build or a Series label is not permission to publish.

## Assets

| asset | role | dimensions | bytes | sha256 | clearance |
|---|---|---|---|---|---|
| `4x5/cover-stack.jpg` | still | 1080×1350 | 158020 | `74bfca5ec71a2f26…` | private-preview; awaiting author clearance; may_publish=false |
| `4x5/cover-page.jpg` | still | 1080×1350 | 276217 | `32563b66ed6346aa…` | private-preview; awaiting author clearance; may_publish=false |
| `4x5/cover-line.jpg` | still | 1080×1350 | 134566 | `9a88de1ad3bee798…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-01-cover.jpg` | carousel | 1080×1350 | 158020 | `74bfca5ec71a2f26…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-02-page.jpg` | carousel | 1080×1350 | 276217 | `32563b66ed6346aa…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-03-line.jpg` | carousel | 1080×1350 | 134566 | `9a88de1ad3bee798…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-04-detail.jpg` | carousel | 1080×1350 | 142525 | `1f8fc5378506482b…` | private-preview; awaiting author clearance; may_publish=false |
| `carousel/carousel-05-detail.jpg` | carousel | 1080×1350 | 142525 | `1f8fc5378506482b…` | private-preview; awaiting author clearance; may_publish=false |
| `reel/p004-version-reel-1080x1920.mp4` | reel | 1080×1920 | 451134 | `45985e289829b61c…` | private-preview; scan-derived; no audio; awaiting author clearance; may_publish=false |
| `reel/poster-1080x1920.jpg` | reel-poster | 1080×1920 | 157014 | `73a10d9a854da026…` | private-preview; scan-derived; no audio; awaiting author clearance; may_publish=false |
| `story/p004-story-assembly-provisional-1080x1920.mp4` | story | 1080×1920 | 590835 | `3a778a3622402d3d…` | private-preview; scan-derived; no audio; awaiting author clearance; may_publish=false |
| `story/poster-1080x1920.jpg` | story-poster | 1080×1920 | 92978 | `0f2fbc0cb23be6cc…` | private-preview; scan-derived; no audio; awaiting author clearance; may_publish=false |
| `widget/tiles/2x1/opening-line.jpg` | widget-tile | 1600×760 | 226984 | `229d95e09efad7f9…` | private test tile; not a public download; awaiting author clearance |
| `widget/tiles/1x1/detail.jpg` | widget-tile | 1080×1080 | 182871 | `8a26d900478ee194…` | private test tile; not a public download; awaiting author clearance |
| `widget/tiles/2x2/page.jpg` | widget-tile | 1080×1080 | 233036 | `c69cc1da4e5ddafe…` | private test tile; not a public download; awaiting author clearance |
| `widget/tiles/wide/opening.jpg` | widget-tile | 1600×760 | 182796 | `3839ea3af8ee5981…` | private test tile; not a public download; awaiting author clearance |
| `widget/p004-widget-kit-private.zip` | downloadable-kit | — | 802060 | `c10c9ff4de10d1c7…` | private zip; no public distribution; awaiting author clearance |

## Clearance

- schema: `versforms.release-clearance.v1`
- status: `awaiting-author-and-evidence`
- author clearance: `null`
- filing evidence: `null`
- shared scan: Unresolved. Page diary3 contains drafts in blocks 0-2 of the same poem; only block 1 is cropped into the kit, but the page-level exposure has no author ruling.
- complete technical exclusion: `false` (T03's 13 withheld page ids and PAL/HF metadata are outside this kit's scope)
- may publish: `false`

## QA

- PIL ink-box geometry at a 390 px display width, plus Apple Vision OCR on the 390 px preview. Geometry is a proxy; physical-device review is still required.

| target | lines | min ink px @390 | median ink px @390 | geometry readable | OCR word recall |
|---|---|---|---|---|---|
| `cover-page` | 9 | 11.89 | 16.0 | yes | 0.884 |
| `cover-line` | 9 | 13.2 | 17.76 | yes | 0.814 |
| `cover-stack` | 9 | 11.55 | 15.54 | yes | 0.721 |
| `carousel-04-detail` | 9 | 13.78 | 18.55 | yes | 0.791 |

## Missing

- Author clearance naming this exact output manifest and its limits.
- Series/Reserve/Archive decision for p004 and for the other diary3 drafts in blocks 0 and 2.
- Author ruling on shared-scan exposure for the diary3 page.
- Original Live Photo / video clips for the 9:16 photo layer (3 s loop) and background layer (4.5 s loop); current layers are still stand-ins.
- T06 D13 identity approval, or the original avatar assets if v3 is not the release identity.
- Physical iPhone Photos-widget test: album picker, render, shuffle, and shared-album behaviour. No iPhone or iOS Simulator is available in this environment.
- Target-journal treatment of Stories (permanent grid/Highlight/expiry) and whether expiry preserves any Reserve status; not yet confirmed for the selected journal.
- GRUW / filing evidence only if a filing claim is made; none is used here.

## Reproduction

```sh
python3 production/kit/kit.py --config production/kit/config/p004.json
```

The manifest is the authority for hashes and clearance state. Re-running after a source, crop, review, identity or clearance change invalidates this output.
