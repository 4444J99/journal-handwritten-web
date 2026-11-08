# Derived layout, keyboard comparison and source-context fixes

Final frozen source head: `6514d8a` on `fix/variorum-source-context`, `/workspace/variorum-source-context-fix`, based on main d635b8d.
Final generated reader head: `00c8717` on `feat/variorum-builder` (PR4), `/workspace/versforms`.
Both working trees clean; no pushes, deployments or content releases.

Scope: the three supplied findings only.

1. Unavailable source ink must not invalidate internally generated coordinates. The prepData unavailable check now applies to source-backed pages; derived pages retain their generated boxes and still undergo bounds/index/count validation. sourceAnchors remains unavailable, and the existing derived safeguards omit synthetic Study ink geometry.
2. Mapped Variorum paragraphs now expose button semantics/pressed state and activate through Enter/Space with preventDefault and the same click path. Comparison state updates across versions in the selected occurrence row.
3. variorumSource rejects non-Journal book modes before selectedSource can return retained Journal focus. Canvas entry and selectedSource note semantics remain unchanged.

Regression evidence:

- `derived-anchor-before.log`: independently reverted anchor fix reproduces thumbnail crash `Cannot read properties of undefined (reading '2')` in thumbStyle on page open.
- `retained-context-before.log`: independently reverted mode guard reproduces a wrong Variorum dialog from retained Journal focus in alternate mode (dialog count 1 versus required 0).
- `comparison-keyboard-before.log`: independently reverted keyboard fix fails default-prevention/activation assertion on actual browser Enter input.
- `source-context-regression.json`: final Chromium regression passes at 1280 and 390 pixels with explicit `technical-text` source anchor unavailable. All views, thumbnails and page/line bitmap rendering work; internal two-line derived boxes survive and unavailable status remains recorded. Existing Study assertions still find no ink rectangles or linked fake source geometry.
- Actual browser Enter and Space input both prevent default, highlight the mapped occurrence in both versions and set their controls' aria-pressed=true.
- HF and Revisions are tested with both null focus and retained focus: V opens no stale modal; native CDP touch pinch closes without wrong comparison. Retained selectedSource still returns the prior line source, verifying note semantics were not changed. Existing three Journal entry paths, both initial and after page navigation, remain passing.
- All earlier mode, stanza, canonical bookmark/reload, contrast, photo, dialog and hidden-bitmap regressions remain passing.
- Existing Variorum browser matrix: 4/4 (`source-context-browser/receipt.json`).
- Focused permalink, notes and Variorum model Node tests: 14/14.
- Generated reader npm tests: 9/9 including both shells/pin parity.
- check.py --write then check.py: OK, 509 references, zero missing, 539 checksums. git diff --check passed.

Matching Studio/public shell SHA-256: `a206cb90fb65ba2871713fe65ed0eb166102b221c21e6ebd968b06c156b299e0`.
Prepared bundle: `/workspace/scratch/source-context-prepared`.
Generated reader package: `/workspace/scratch/source-context-package`.
Full file-hash receipt: `source-context-package.json`; readable tracked receipt and delivery README/summary updated.
No new shipped test API; observation helpers remain local browser fixture instrumentation.

Frozen after the three tested fixes. Root coordinates source PR148 and reader PR4 review/merges.
