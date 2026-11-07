# Variorum and Builder

## Produced

Implemented the approved handoff: source adapters, immutable persistence, Studio Parts/Builder, promotion, reader spread/typeset rendering, publication gates and independent Python parity, recoverable exports/imports, tests and generated reader package. See ../verification/variorum-2026-11-07/README.md for evidence and operations.

## Author decisions

The author requested verification, review and implementation, then explicitly supplied the complete implementation handoff. Its numbered provisional parts, preserved identities, author-only Builder, release gates and reader entry defaults govern implementation. No additional artistic decisions or release approvals were inferred.

## Plan / next steps

Implementation and local review complete. Deployment uses the existing exact-output workflow and matching shell pin. Physical iPhone acceptance and author glyph evidence remain real-world inputs, not coding prerequisites.

## Status

Local source and reader branches contain committed implementation; no live resources changed. Feature checks, browser evidence, local Pages/D1/R2 publication and independent parity pass. Full Python suite retains one timeout-test failure reproduced on untouched baseline. Full CI must not be reported green.

## Reader review follow-up

Verified and fixed review findings in the canonical reader: supplemental layout membership, composite photo canvas and thumbnails, scan-page lookup, accepted parsed readings, modal keyboard ownership, and Study rendering without synthetic source geometry or image requests. Added real Chromium regressions at desktop and phone widths; the same harness reproduces the Type-view exception on baseline e359698. Native single-version rendering remains supported. Regenerated both public shells and the matching Studio pin without publishing poem content.

Housekeeping PR #143 subsequently resolved the baseline timeout test; integrated feature CI passed all five suites at a4690b64d93cde2d70a5feb015481cbe0833c249 (verification receipt: integrated-ci.json). Independent review approved the reader fixes. The generated reader follow-up is commit 830c8db; it is local and unpushed.

Late reader review fixed derived transition bitmap snapshots when the live item is hidden. Snapshot drawing now receives a visible copy without changing the live item. Chromium checks both text and photo page/line bitmaps at desktop and phone widths, with nontransparent pixels and the hidden state preserved. Regenerated matching public shells and Studio pin; no content release.

Final review moved hidden-bitmap observation entirely into the local browser harness through source instrumentation; the published reader has no additional mutable debug method. The same Chromium regression passes and the matching package/pin was regenerated.

Additional verified reader fixes preserve page-level Variorum entry without a selected line and frozen stanza breaks in Words, Scan and Study. Variorum alone falls back to the current page piece/version; note anchors retain their line-scoped behavior. Chromium exercises button, keyboard and native touch pinch before/after page navigation at both widths and measures the stanza gaps. Matching shells/pin regenerated; no content release.

Scoped review restricts the new no-line Variorum fallback to Journal mode; Hand ↔ Font and Revisions cannot resolve a stale journal page. Real-browser keyboard and touch pinch checks for both alternate modes pass without a wrong comparison modal.

Final scoped bookmark fix opens photo-only supplemental versions in Scan so the released photograph is visible on a stable piece/version link. Versions with transcription retain their Words route. Chromium verifies the photo-only bookmark loads its image at both widths, and the same check fails against the previous source. Regenerated matching shells/pin; no release.
