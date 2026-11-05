# 01 · Image processing and upscaling options for page scans

| | |
|---|---|
| Chat | https://claude.ai/chat/69d14aba-7eb2-476a-ab7b-6e90d7a98535 |
| Exchange | 01 of 1 · 2026-10-27 |
| Issue | #25 |

## Asked
Whether there are methods to process the journal page images, to upscale them or improve them in some other way.

## Answered / produced
- No files or artifacts; answer only.
- Faithful (deterministic) methods: rescan/rephotograph at 600 dpi or more; check whether the 2015 spreads exceed the published crops in resolution; classical cleanup (deskew, perspective correction, lighting flattening, contrast, denoise, sharpening, show-through reduction) with OpenCV or ImageMagick; ink/paper separation into a transparent stroke layer; vectorization of binarized ink with potrace to SVG.
- Inventive method: AI super-resolution (Real-ESRGAN, SwinIR), display use only, since it can alter letterforms; not for transcription checks, the font, or copyright deposits.
- Reading aid: HTR (Transkribus, TrOCR) on cleaned images as a second opinion on the 306 uncertain readings.
- Proposed three tiers per page (checksummed master, cleaned, display) with the recipe recorded in the manifest.

## Author decisions
None. The chat ends with Claude's offer unanswered.

## Plan
- **Claude suggestion**, open: keep three image tiers per page with a per-page recipe in the manifest.
- **Claude suggestion**, open: restrict AI super-resolution to display images.
- **Claude suggestion**, open (offered, not run): side-by-side trial of the three tiers on a few clean and a few hard pages from the etceter4 repo.
- **Claude suggestion**, open: run HTR as a second opinion on the 306 uncertain readings.
- **author**, open: decide whether a rescan of the notebook at 600 dpi or more is possible.
