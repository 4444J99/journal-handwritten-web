# Reader navigation and About

**Date:** November 6, 2026 (America/New_York; tool work may fall on November 7 UTC).

## Produced

- Updated the [reader menu design](../superpowers/specs/2026-11-06-reader-menu-design.md) and [implementation plan](../superpowers/plans/2026-11-06-reader-menu.md) to distinguish the original engineering proposal from the later approved drawing-based direction.
- Prepared the private [About writing brief](../audience/about-writing-brief.md), including prompts, dated source limits and insertion instructions. No creative or interpretive About statement was written for the author.
- Added the same scoped update to `docs/plan.md` and `claude/plan.md`, and indexed this session.
- Implemented the source reader and traced author assets; independently verified 66 WebKit checks with no script/asset failures. The final source SHA-256 is `fa881488d207db1532cd689f6d41fd4b2b37976a5e978b7164be69681c80e3fa`.
- Rebuilt and tested the public package, with identical production/staging shells and matching versioned Studio pin `2eafbf061b5b0b8081545d1822885d94a462ae30f12953f1f9b74994a73ef3b3`. The [verification receipt](2026-11-06-reader-menu-verification.json) binds the checks to those exact artifacts. Branch/PR integration and hosted deployment observations are recorded by the integrator in the associated pull requests.

## Review correction and delivery

[Private PR #139](https://github.com/4444J99/journal-handwritten-web/pull/139) and [public PR #3](https://github.com/4444J99/versforms/pull/3) carry the paired source/template changes. Both initial heads received successful Cloudflare preview and Semgrep checks. Their automated review then identified a keyboard regression: closing Menu restored launcher focus, but its button guard blocked reader shortcuts. The new test reproduced Escape followed by ArrowRight failing before the fix. A launcher-only exception now preserves native Enter/Space and allows existing navigation, zoom and version keys when controls are closed. All 66 final WebKit checks pass.

The 61-check result on the earlier artifact remains historical evidence; it did not cover the reported sequence. The verification receipt retains both the failing regression baseline and the corrected result. Private GitHub Actions failed without available step/log evidence, so its current cause is unverified. Final head, merge and production-deployment receipts belong in the PRs; preview success alone is not a production or authenticated-runtime check.

## Author decisions

1. The menu is difficult to discover and trigger; its controls and hierarchy are unclear. It needs to be more intuitive.
2. The author needs to write an About/info explanation of what the project is.
3. He requested **three options before implementation**, then clarified that the menu should remain mainly hidden, with a small icon or drawing as its entrance.
4. He supplied a photograph containing a crown and a heavy hamburger drawing and asked for an assessment.
5. He accepted the assistant's recommendation of a bold hamburger launcher with a small handwritten `menu` label and the crown inside Menu/About. This was an accepted recommendation, not his originally specified visual arrangement.
6. He approved a small backing that reverses the canvas/text color roles.
7. He subsequently directed the work to proceed with all authorized tasks and resume the original menu/About work.

The standing authorship boundary remains: creative and interpretive presentation text is the author's; technical interface writing may be AI-written. This project remains distinct from ETCETER4, the author's music. No new release cadence, poem selection, public About text or poem-publication decision is inferred from the menu direction.

## Plan / next steps

### Earlier proposal retained as history

The first engineering proposal used a permanently visible text-labeled Menu launcher, grouped controls and a combined About/help panel. It had not been approved as a visual design. The later author directions supersede the launcher proposal. This history is retained so that implementation assumptions are not recorded as earlier author decisions.

### Current implementation plan

- Use the author's hamburger drawing in compact `#b-menu`, with a small handwritten `menu` label, accessible name Menu, reversed color backing and a usable touch target. Keep the full controls hidden until opened.
- Group and label the controls within `#ov`; provide explicit dismissal through `#menu-close`, reliable focus return and scrollable layouts on short/narrow screens.
- Provide separate About (`#b-info` → `#infop`) and How to explore (`#b-help` → `#helpp`) destinations. Keep the crown in Menu and About. Retain the existing source/transcription hooks `#i-src`, `#i-tr` and `#i-page`.
- Keep `#about-author` genuinely empty and hidden until the author supplies the exact text he wants presented. Maintain practical instructions separately in How to explore.
- Verify the implemented desktop, phone-emulated and keyboard flows, inspect light/dark screenshots, build the candidate engine and record its exact hash. The integrator refreshes intentional manifest entries and records integrity/integration results.
- Reconcile against the current remote head before final delivery. Engine activation follows the existing exact-output review and matching Studio shell-pin process; source implementation does not clear a poem for publication.

The separate destinations, DOM IDs, practical help wording and detailed interaction behavior are implementation choices within the accepted approach. Any remaining editorial prompts in the writing brief are suggestions for the author, not adopted creative text.

## Status

**Implementation and local verification complete after the review correction; PR #139 and PR #3 are open at this record’s preparation. Final integration is tracked in those pull requests.** The inspected private main is `9c0e9c565fb9d7bef3a68b21faa744010a401f60`; no open PRs were reported at that fresh inspection. The local `reader-source` folder is a snapshot, not a Git checkout. Neither that baseline nor this documentation pass establishes a new commit, merged PR, deployed engine or posted poem.

The author still supplies the About description. Browser emulation does not establish physical-iPhone acceptance. No public creative copy is invented to fill the empty section.

### Sources and limits

- Current author directions in this conversation govern the menu revision. Historical instructions and approvals remain evidence, not permission for unrelated new actions.
- `CLAUDE.md` was read directly for the session-log convention and standing authorship/presentation rules.
- [The mark provenance record](../audience/reader-marks-provenance.json) was read directly. It identifies the supplied photograph as `libfile_ce18517409448191a7ccb21668cee0d0`, SHA-256 `e83fbf423fa1568f0f7a33303392e5b3308e4d577d1bb5bc6bec442cb17c4e89`, and records the exact source crops, ink isolation, upright rotations and resulting SVG hashes. The integrator reports visual inspection of the crops and prepared vectors; this documentation pass does not substitute for browser acceptance.
- The accessible October 28, 2026 `15-plan3.md` records the journal source and 100-poem goal. The repository plans retain that dated history; counts and goals are not claims of current publication.
- `docs/audience/identity-status.md` (`T06-ID-01`) was read directly. Its referenced I49 / X49 and X41 exchanges and linked source register were not independently available in this snapshot. The name-meaning phrase and later weekly decision are attributed to that record, not treated as newly retrieved original statements.
- Private shared-memory packet `2026-10-16-v1.1`, sanitized projection `2026-10-16-v1.1-r2`, in project `g-p-6a10bcb4ada4819194e881431212101a` remained inaccessible. `interpretation.md`, `cloud-master-context.md` and `cloud-source-ledger.json` were not retrieved. No unseen history, fact or approval is attributed to those sources.
