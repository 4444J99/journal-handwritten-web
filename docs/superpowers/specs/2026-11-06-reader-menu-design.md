# Reader menu and About design

**Status:** Author-approved visual direction; implementation and validation are in progress. Exact checks, engine hash and remote delivery belong in the integrator's closeout receipt.

## Request, decisions and history

On November 6, 2026 (America/New_York), the author reported that the menu is hard to discover and trigger, that its buttons and hierarchy are unclear, and that he needs to write an About/info explanation of the project.

The initial engineering proposal used a permanently visible text-labeled Menu launcher and a grouped control panel. Alternatives in that proposal were an introductory hint for the hidden trigger or permanently visible controls. That proposal was not an author-approved visual design and is retained here as history.

The author subsequently asked for **three options before implementation**, clarified that the menu should remain mainly hidden behind a small icon or drawing, and supplied a photograph containing a crown and a heavy hamburger drawing for assessment. He accepted the assistant's recommendation to use the bold hamburger with a small handwritten `menu` label as the launcher and the crown within Menu/About. He also approved a small backing with the canvas/text color roles reversed, then explicitly directed the work to proceed and resume the original menu/About tasks. The visual arrangement was an accepted recommendation, not a design first specified by the author. Those later scoped directions supersede the earlier text-button proposal.

The inspected private main is `9c0e9c565fb9d7bef3a68b21faa744010a401f60`; the local working material is a snapshot, not a Git checkout. On that baseline the control bar is hidden, icon explanations depend on hover, controls dismiss after 2.8 seconds (6 seconds for the expanded sheet), and phones add another disclosure. The public reader was blank at the session's inspection. These observations describe the inspected state, not the result of this change.

## Current design

The small, persistent launcher uses the author's heavy hamburger drawing, a small handwritten lower-case `menu` label and the accessible name **Menu**. Its backing takes the current canvas text color; the drawing takes the current canvas background color. Both roles switch with the reader theme. The visible mark stays compact while the button provides a minimum 48-pixel target and safe-area spacing.

The prepared assets are `site/ui/author-menu.svg` and `site/ui/author-crown.svg`. [The provenance record](../../audience/reader-marks-provenance.json) identifies the supplied photograph, its SHA-256, crop regions, upright rotations, retained ink and exact SVG hashes. The recorded method traces thresholded pixel boundaries; it does not create new drawing content. The photograph and neighboring writing remain outside the reader assets. The integrator owns the tracer, assets and provenance record.

All full controls remain hidden until deliberately opened. A single tap, click or keyboard action opens the complete menu. It stays open until dismissed or an action intentionally transfers the reader to the selected destination. Labels, group headings and selected states explain the controls. Navigation and the separate About / How to explore destinations precede context-specific display and arrangement controls. The menu scrolls within narrow or short viewports. The author's crown appears inside Menu and About.

| Element | Implementation contract |
| --- | --- |
| Launcher | `#b-menu`, accessible name Menu; compact drawing and label, inverse backing |
| Full menu | `#ov`; `#menu-close` dismisses it |
| About | `#b-info` opens `#infop`; retains source/transcription information and the crown |
| How to explore | `#b-help` opens `#helpp`; practical instructions for the implemented controls |
| Author description | `#about-author`, initially hidden and empty inside About |
| Existing public-builder hooks | Preserve `#i-src`, `#i-tr` and `#i-page` |

The separate destinations, element IDs and practical help wording are implementation choices within the accepted approach. They do not add an author-written project description or a release decision.

## Interaction acceptance

Keyboard and pointer dismissal must agree. Hidden controls leave the tab order; native buttons retain Space/Enter behavior; Escape and close actions restore usable focus. A dismissal gesture must not also activate the canvas. Focused menu/panel controls must not send navigation keys to the poem underneath. Opening About or How to explore must make the destination clear and provide a reliable return path.

Check phone tap discovery, desktop pointer and keyboard use, light/dark inversion, landscape overflow, selected-state clarity, and preservation of normal reader interaction after dismissal. Browser emulation is distinct from physical-iPhone acceptance. These are acceptance requirements, not claims that verification has already passed.

## About and boundaries

The author writes the description of what the work is. [The private writing brief](../../audience/about-writing-brief.md) offers prompts, dated evidence and exact insertion instructions. `#about-author` remains truly empty and hidden until supplied author copy is ready; no generated statement, inferred biography or placeholder is presented. Practical instructions belong in the separate How to explore panel.

Menu/About work does not select or clear poems, alter source/review records, or itself activate public output. Existing exact-artifact review and matching Studio shell-pin requirements apply to an engine activation. The inaccessible private packet `2026-10-16-v1.1` / `2026-10-16-v1.1-r2` and its `interpretation.md`, `cloud-master-context.md` and `cloud-source-ledger.json` are source limits, not unseen authority. Earlier plans and approvals remain historical evidence.
