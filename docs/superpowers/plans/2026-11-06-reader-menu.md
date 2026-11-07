# Reader Menu Implementation Plan

> **For agentic workers:** Use the existing source reader and verify the actual browser behavior. The local folder is a snapshot, not a Git checkout. The integrator owns remote reconciliation, the final artifact and the delivery receipt. This plan does not clear a poem for publication.

**Goal:** Make reader controls discoverable and understandable, and establish a place for the author's About text.

**Architecture:** Preserve the single reader template, existing control identities and reader state transitions. Use the author's bold hamburger drawing for a compact launcher, with inverse backing and a small handwritten label. Keep the full grouped menu hidden until opened. Provide separate About and How to explore destinations; reserve About copy for the author.

**Tech Stack:** Existing HTML, CSS and JavaScript; repository Python integrity/build tools; installed Playwright for browser acceptance.

**Spec:** `../specs/2026-11-06-reader-menu-design.md`.

## Decision history

The initial plan proposed a permanently visible text-labeled Menu control without an approved visual design. The author then requested three options before implementation, specified a mainly hidden menu with a small icon/drawing, and supplied a crown and heavy hamburger photograph for assessment. He accepted the assistant's recommendation of a bold hamburger launcher with a small handwritten `menu` label and the crown inside Menu/About, approved the small backing with canvas/text colors reversed, and subsequently directed all work to proceed, including the original menu/About task. The approved direction replaces the earlier launcher proposal; it does not authorize AI-written creative About text. Separate About / How to explore destinations and DOM IDs are implementation choices within that approach.

## Global constraints

- No AI-written creative or interpretive reader copy.
- Full controls remain hidden until requested. The compact drawing and inverse backing follow the later author direction.
- Do not change poem content, source/version identities, release lists, noindex, access settings or public pointers.
- Preserve `#i-src`, `#i-tr`, `#i-page` and public-builder transformation contracts.
- Preserve current remote work. The integrator rechecks the remote head and records the exact reviewed branch/PR outcome; no remote result is claimed by this snapshot.

## Review focus

Phone tap discovery, landscape overflow, hidden keyboard focus, Escape/outside dismissal without a second canvas action, and text/selected-state clarity require browser checks. The actual physical iPhone remains a separate owner acceptance surface.

## Task 1: Reader controls

**Files:** `site/index.html`; `tools/verify_reader_menu.mjs`.

The integrator supplies `site/ui/author-menu.svg`, `site/ui/author-crown.svg`, `tools/trace_reader_marks.py` and `docs/audience/reader-marks-provenance.json`. Consume the traced marks and retain their provenance; the original photograph is not a reader asset.

- [x] Record baseline behavior and implement `#b-menu` using the author-supplied drawing, inverse backing and accessible Menu name.
- [x] Add the labeled grouped controls inside `#ov`, deliberate `#menu-close` dismissal and the crown inside Menu.
- [x] Provide separate About (`#b-info` → `#infop`) and How to explore (`#b-help` → `#helpp`) destinations.
- [x] Verify tap, click, Space/Enter, Escape, focus restoration, light/dark inversion, selected state and narrow/short viewport scrolling.
- [x] Inspect phone/desktop screenshots and rerun the relevant reader integration checks.

## Task 2: About and source record

**Files:** `site/index.html`; `docs/audience/about-writing-brief.md`; this plan and its spec; `docs/chats/2026-11-06-reader-navigation-and-about.md`; `docs/chats/README.md`; `docs/plan.md`; `claude/plan.md`. The integrator owns generated artifacts and `MANIFEST.sha256`.

- [x] Provide technical help in `#helpp`, the crown and existing source details in `#infop`, and a genuinely empty hidden `#about-author`; verify panel opening and return focus.
- [x] Document a concise writing brief and author-copy insertion instructions using dated accessible sources, without supplying an artist statement.
- [x] Preserve the initial proposal as history and record the author's later visual decisions in the spec, session record and both plan copies.
- [x] Rebuild the candidate engine privately with pinned dependencies; record its exact hash and activation dependency.
- [x] Refresh the manifest only for intentional changes and run `python3 tools/check.py`.
- [ ] Independently review the diff, complete the integrator's authorized delivery sequence and record its exact remote head/PR outcome.

## Validation and residuals

The final source `92a04f8d3ea918079fa2961983e49a08658a66447f090716da9d3f6dae7a3d10` passed 61 WebKit checks with zero script/asset errors, 11 public-metadata tests, and the repository integrity check (509 references, 536 checksums). The generated public package passed 9 tests. The production/staging shell and the versioned Studio pin agree at `35bb01c5340f2501a4f949f91d989a729e21d9261239b9f94784562d22185cec`. See [the verification receipt](../../chats/2026-11-06-reader-menu-verification.json). The integrator will record subsequent integration and hosted deployment outcomes in the associated pull requests; this pre-integration snapshot does not itself prove deployment.

The author still supplies the About words. Exact engine activation uses the existing review and matching Studio shell-pin process; successful UI verification does not publish a poem or establish physical-device acceptance. The original private context packet `2026-10-16-v1.1` / `2026-10-16-v1.1-r2` remains inaccessible.
