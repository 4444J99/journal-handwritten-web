# Variorum and Builder implementation ledger

Authority: user implementation handoff of 7 November 2026 supersedes earlier pending-decisions documents.

## Decisions
Numbered provisional stanza groups, explicit acceptance, no invented source text, preserved identities and immutable composite history. Existing vf_docs/vf_revs, JWT middleware and publication fencing remain authoritative. No deployment, remote data write or poem release is performed.

## Tasks
- [x] Baseline: branch feat/variorum-builder; source validation, notes map and integrity pass.
- [x] Shared source/parts/recipe model and tests.
- [ ] Conflict-safe persistence, exports and recoverability.
- [x] Integrated Studio workbench.
- [ ] Frozen typeset rendering and publication adapter.
- [x] Reader spread and lifecycle.
- [ ] Integration checks and handoff receipts.

## Rulings
- Preserve canonical source bytes; supplemental versions are stand-off records.
- Missing sources remain unavailable; canonical p001 has two versions.
- Public staging cannot host unverified drafts.

## Current implementation evidence

The author handoff replaces the former “awaiting decisions 1–4” checkpoint. Model tests resolve actual p001 identities, retain sparse repeated occurrences and frozen text, and require current author verification. SQLite API tests exercise one-winner saves, exact retries, fences and explicit re-materialization after correction. The Studio workbench supports provisional maps, linked pieces, contiguous mouse/touch/keyboard selection, composite recipes, history and explicit promotion. Browser fixtures exercise the actual modules at 1280×900 and 390×844 in both themes; these are emulated tests, not physical iPhone evidence.

Source import retains content-addressed originals under private source/external/.versions. Generated layout pages stay internal to the reader, carry derivedLayout metadata, and do not add source membership or handwritten ink evidence. Rendering waits for the embedded font before measurement.

Publication, restore reconciliation and final full CI remain under integration verification. No remote application or source database has been changed.
