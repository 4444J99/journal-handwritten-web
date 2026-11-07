# Journal piece — control inventory

Nov 6, 2026 · @anthony james padavano

Every control in the merged piece (artifact version 4, read from its code on this date) is one of five kinds, and today all five look the same: a round icon button in a row. A redesign starts by giving each kind its own look and its own place.

## Chosen direction: zoom is the hierarchy

Agreed Nov 6, 2026: there is one space, and depth replaces the menus. Each depth shows only what applies there, and the same few gestures work at every depth, so nothing needs a label. Aims: simplicity, minimalism, clarity, usable without text.

&#91;embedded content: zoom as hierarchy · 4 depths, 4 gestures\]

What this removes: the Journal / Constellation switch, Whole, and the separate Revisions, Drafts, Versions, Typeface, Hand ↔ Font, Scan and Words controls. Visible icons drop from about 58 to under ten: one global mark, the arrangement control at archive depth, and small marks on the work itself.

On a first visit the work teaches once, without words: a page peels back a sheet, then a line shifts to type and back.

Open within this direction:

- [ ] Whether Study (scan beside words) survives as a state, or is simply the halfway point of the hand-to-type drag
- [ ] What appears at depth 4, once the roots and glyphs phase is designed
- [ ] Whether a long press is safe on iPhone, where it also opens the system text menu

## Where every current function goes

Nothing from the current menu is dropped: each control and setting either moves into a gesture, into the one global mark, or into a mark on the work. Three Study controls were missing from the inventory above (Author's hand, Outline lines, 2015 spread) and are added here. "Prototype" is the state of the gesture prototype (Minotaur Depths) as of 2026-11-06.

| Current control or setting | New home | Prototype |
| --- | --- | --- |
| Journal (place) | Tap or pinch into a page | Yes |
| Constellation (place) | Pinch closed, or tap the empty ground | Yes |
| Current content / mode readout | Not needed: the state is visible in the work | — |
| Current arrangement / view readout | The arrangement icon pictures the next layout | Partly |
| Search | Global mark | No (shown, disabled) |
| More | The global mark | Yes |
| Lines | Arrangement control also sets the unit (pages or lines); its picture shows which | No |
| Pages | Same control | Pages only |
| Unfold (pages far, lines near) | Becomes the default behaviour of depth | Partly |
| Typeface | Drag to type, at every depth including the archive | Poem and line depth only |
| By poem | Arrangement control | No |
| Scatter | Arrangement control | Yes |
| Spiral | Arrangement control | Yes |
| Whole | Pinch closed at archive depth; key 0 | No |
| Journal mode | Poem depth | Yes |
| Revisions mode (replay a page) | Swipe at line depth; a play action in the global mark runs the whole page | Line by line only |
| Hand ↔ Font mode, slider, play | Drag is the slider; play runs the crossfade | Drag only |
| Scan | Drag fully to hand | Yes |
| Words | Drag fully to type | Over the page only |
| Study (scan beside words) | Proposed: on wide screens or in landscape, scan and type sit side by side | No |
| Marks on / off | The step chosen at line depth applies to the whole page | Line only |
| Author's hand (study text in your font or a standard font) | Proposed: dragging past full type switches to a standard font | No |
| Outline lines (line boxes on the scan) | Proposed: shown while dragging, as the places the type lands | No |
| 2015 spread (recovered text on 8 cropped pages) | Press and hold on one of those pages | No |
| Light / dark | Global mark | Yes |
| Info | Global mark | Yes |
| Page strip | Spiral arrangement is notebook order; page edges step through it | No |
| Previous / next page (edges) | Tap a page edge at poem depth | No |
| Step back / play / step forward | Swipe at line depth; play in the global mark | Swipe only |
| Draft dots | Sheets underneath the poem | Yes |
| Earlier / later version | Swipe at poem depth | Yes |
| Version dots (dated) | Sheets; press and hold shows the date | Partly |
| Poem and page pickers in the Revisions and Hand ↔ Font panels | The poem or page you are on | — |
| Search results open in the journal or the constellation | Kept: a result opens at its depth | No |
| New layout each visit | Kept | Yes |
| Link keeps the current view | Kept | No |
| Theme remembered | Kept | Yes |
| Keys (B, /, \[ \], 0, + −, Enter, Space, Esc) | Kept; Enter / Esc / arrows mapped to depth and time | Partly |
| Long-press a line to open it in the journal; pinch closed to return | Tap or pinch in; pinch closed | Yes |
| Reduced motion | Kept | Yes |

## The five kinds

| Kind | What it is | Test | Current examples |
| --- | --- | --- | --- |
| Place | Which space you are in; changing it changes everything else | Does pressing it swap the other controls? | Journal / Constellation |
| Setting | A lasting choice from a closed set (or an on/off toggle) that changes how things are shown | Does it stay chosen after you look away? | Lines / Pages / Unfold / Typeface; By poem / Scatter / Spiral; Scan / Words / Study; marks on/off |
| Action | A one-time command; nothing stays selected | Is there nothing to show as "on" afterwards? | Whole; play; step back / forward; earlier / later version |
| Contextual | Exists only because of what you are looking at | Does it appear only for some pages, poems or modes? | Page strip; Revisions panel; Hand ↔ Font panel; Versions panel |
| Global | Works the same everywhere | Would it make sense in any place and mode? | Search; Light / dark; Info |

Two controls in the bar are none of these: the two "current" buttons only show the active choice and open the full menu. They are readouts acting as buttons.

## The tree today

&#91;embedded content: menu tree today · built solid, planned dashed\]

Everything under a place box disappears when you switch place; everything under Mode disappears when you switch mode. Only the bottom row stays put.

## Inventory

Thirty-three controls, grouped by where they sit today. "Problem" notes what makes each one hard to read; blank means it reads fine.

| Control (icon) | Kind | Lives in | Shown when | Changes | Problem |
| --- | --- | --- | --- | --- | --- |
| Open book (Journal) | Place | Bar | On the canvas | Swaps to the journal; replaces every canvas row with journal rows | Looks like any other button; same name as a journal mode |
| Constellation | Place | Bar | In the journal | Swaps back to the canvas | Same as above |
| Current content / mode | Readout + menu | Bar | Always | Opens the full menu | Icon changes with state; on the canvas it shows content, in the journal it shows mode |
| Current arrangement / view | Readout + menu | Bar | Hidden in Hand ↔ Font | Opens the full menu | Same; sometimes missing |
| Magnifier (Search) | Global | Bar | Always | Opens the search panel |  |
| Three dots (More) | Menu | Bar | Always | Opens the full menu | Does exactly what the two readouts do |
| Wavy lines (Lines) | Setting | Canvas: content | Canvas | Each mark is one handwritten line |  |
| Page with writing (Pages) | Setting | Canvas: content | Canvas | Each mark is a whole scan | Same icon idea as Scan in the journal |
| Dashed page + lines (Unfold) | Setting | Canvas: content | Canvas | Pages far away, lines close in | A zoom behaviour placed among content types |
| A + a (Typeface) | Setting | Canvas: content | Canvas | Lines set in Etceter4 Diary | Same idea as Hand ↔ Font in the journal |
| Circles (By poem) | Setting | Canvas: arrangement | Canvas | Clusters by piece; new layout each visit |  |
| Scattered dashes (Scatter) | Setting | Canvas: arrangement | Canvas | Free scatter; new each visit |  |
| Spiral | Setting | Canvas: arrangement | Canvas | Notebook order |  |
| Four corners (Whole) | Action | Canvas: arrangement row | Canvas | Zooms out to fit | An action sitting among settings |
| Open book (Journal) | Setting | Journal: mode | Journal | Page-by-page reading | Same icon and name as the place button |
| Lines + pen (Revisions) | Setting | Journal: mode | Journal | Replays one page's revision steps | Name shared with the marks toggle and a panel |
| Squiggle + A (Hand ↔ Font) | Setting | Journal: mode | Journal | Crossfades hand to font | Duplicates Typeface |
| Page with wavy lines (Scan) | Setting | Journal: view | Journal mode; Revisions mode on narrow screens | Photo only | Hidden in other modes without explanation |
| Page with straight lines (Words) | Setting | Journal: view | Same | Transcription only | Same |
| Scan beside text (Study) | Setting | Journal: view | Same | Both side by side | Same |
| Struck S (marks) | Setting (toggle) | Journal: view row | Same | Revision marks on or off in the text | Labelled "Revisions marked"; reads like a mode |
| Light / dark | Global | Display row | Always (inside the menu) | Theme | Global control buried in the menu |
| i (Info) | Global | Display row | Always (inside the menu) | Opens notes and keys | Same |
| Page thumbnails | Contextual | Strip above bar | Journal mode | Jumps to a page |  |
| Poem buttons | Contextual | Revisions panel | Revisions mode | Which poem to replay | Appear only after a mode change |
| Step slider | Contextual | Revisions panel | Revisions mode | Scrubs through revision steps |  |
| Draft dots | Contextual | Revisions panel | Revisions mode | Jumps to a draft | "Draft" vs "version" unclear |
| Back / play / forward | Action | Revisions panel | Revisions mode | Steps through revisions | Same icon family as Hand ↔ Font play |
| Page buttons | Contextual | Hand ↔ Font panel | Hand ↔ Font mode | Which page to crossfade |  |
| Hand ↔ font slider + play | Setting + action | Hand ↔ Font panel | Hand ↔ Font mode | Crossfade amount |  |
| Earlier / later version | Action | Versions panel | A focused stack on the canvas, or a journal page that has versions | Moves through versions | Appears with no visible cause |
| Version dots | Contextual | Versions panel | Same | Jumps to a version; dated or n/N | Same |
| Page-edge arrows | Action | Screen edges | Journal, near an edge | Turns the page | Not part of the bar at all |

## Interactions

Most of the "buttons disappear" effect comes from two presses: the place switch and the journal mode buttons. Each rebuilds the bar without showing what changed.

| You do | Appears | Disappears or changes meaning |
| --- | --- | --- |
| Press Journal (place) | Mode row, view row, page strip; readouts now show mode and view | Content row, arrangement row, Whole; the canvas |
| Press Constellation | Content and arrangement rows; readouts show content and arrangement | Every journal row and the strip |
| Long-press a line or page on the canvas | The journal, open at that page | Same as pressing Journal, but with no button pressed |
| Pinch closed in the journal | The canvas | Same as pressing Constellation |
| Journal mode → Revisions | Revisions panel | Page strip; view row (wide screens only); second readout may go blank |
| Journal mode → Hand ↔ Font | Hand ↔ Font panel | Page strip; view row; second readout |
| Back to Journal mode | Page strip; Versions panel if the page has versions | The mode's panel |
| Tap a version stack on the canvas | Versions panel | Nothing else; Esc or a tap outside closes it |
| Open a poem to read | — | All controls hide |
| Press either readout or More | The whole menu | — (the same press again closes it) |
| Leave the bar for 2.8 s (desktop) | — | All controls hide |

## Planned (draw greyed out)

Twenty-five planned features would add or change a control. They come from plan.md, the project memory, past chats and the issues in the private repository (read today, #1–#138). Statuses are as recorded there; change the dropdown as you decide.

| Feature | Would appear as | Kind | Attaches to | Status | Source |
| --- | --- | --- | --- | --- | --- |
| Poem number and version label ("12/100 · v3") | Small readout on a focused poem | Contextual | Poem | Needs decision | plan.md; #62, #63 (numbering method open) |
| Footnotes | Marks on words or lines; tap opens the note | Contextual | Word, line | Decided | memory; #17 |
| Endnotes, response end note, academic note, citations | A notes panel at the end of a poem | Contextual | Poem | Decided | plan.md prep list; #17 |
| Personal reflection notes, dual-dated (poem date + note date) | Endnote layer; both dates on tap | Contextual | Poem | Decided | memory; #18 (dual dating proposed) |
| Notes data and contribution review | Not visible yet; studio side | — | — | Built privately | PR #126 (title only checked) |
| Read aloud in your synthetic voice | Play on a poem | Action | Poem | Decided | memory; #22–#24 |
| Forward / backward reading (Red Room) | Direction switch beside play | Setting | Poem | Decided | memory; #24 |
| Ambient sound from your voice | Sound on/off | Global | Everywhere | Needs decision | memory; #35 (palette and silent-switch choices open) |
| Puzzle layer: Key Sheet and page:line:word book cipher | A faint lock mark on pages; a key panel | Contextual | Page, line | Proposed | memory (game element wanted); #52, #53 |
| Revisions dig (struck words revealed) | Gesture or toggle on a page | Contextual | Page | Proposed | #53 |
| Cut-up views: fold-in, erasure versions, tap a line to see its source page | New view options; source link on a line | Setting + contextual | Line, poem | Proposed | #55 |
| Reader cut-ups (visitor rearranges lines) | A mode | Setting | Poem | Needs decision | #55, #56, #109 |
| Per-visit variation (seed, time, season, return visits) | No button; a line in Info | — | — | Proposed | #32 |
| Concordance blooms (tap a word, its other occurrences appear) | Tap behaviour | Contextual | Word | Needs decision | #32, #109 (not to be built until decided) |
| Opt-in sensors (motion, weather, location) | One permission switch | Global | Everywhere | Needs decision | #32, #109 |
| Participation layer (responses, readings, contributed handwriting) | Separate layer on/off; a contribute entry | Setting + global | Everywhere | Needs decision | plan.md; #64, #109 (type open) |
| Roots and glyphs (LingFrame) | A deeper zoom level below the line | Setting (depth) | Line, word | Decided | plan.md; #12 (later phase) |
| Other scripts (Greek, Cyrillic, Hebrew renderings) | Script choice beside Typeface | Setting | Line | Proposed | #33 |
| Read progress | Faint marks on read items | Contextual | Item | Proposed | #16 |
| Next / previous on a focused poem | Two arrows on the focused poem | Action | Poem | Proposed | #16 |
| Email signup | One entry in Info or the global row | Global | Everywhere | Proposed | #71 |
| Member layers (versions and notes for members, writing circle) | A lock on member-only layers | Contextual | Layers | Proposed | plan.md business model |
| Numbered print edition per poem | A link on the poem | Action | Poem | Proposed | plan.md business model |
| Final version vs drafts as layers ("Nothing shines") | Changes what the Versions panel shows | Contextual | Version stack | Needs decision | plan.md open item 4; #20 |
| Transcription as page text (search, screen readers) | No button | — | — | Proposed | #71 |

Not controls, but they shape the menu: the public site carries only posted poems (memory, 2026-11-05), so most items exist only as they are released, and an app is wanted later (memory).

## Words that collide

Six ideas each go by more than one name, or one name covers more than one idea. Each needs a single name (or a single icon) before any drawing settles.

| Word now | Means | Also used for | Note |
| --- | --- | --- | --- |
| Journal | The place (book side) | A mode inside that place | Two different buttons with the same icon |
| Revisions | Cancellations and insertions within one page, replayed | The marks toggle ("Revisions marked") and the replay panel | One word for a mode, a toggle and a panel |
| Drafts | The same poem written more than once in the notebook | Dots in the Revisions panel | Historical, from 2014–2015 |
| Versions | New handwritten versions made now, stacked over older ones | The Versions panel; "v3" in a poem label | Drafts and versions are the same kind of thing at different times |
| Hand / font | Typeface on the canvas | Hand ↔ Font mode in the journal; a planned script choice | Three controls for one axis |
| Pages / Scan | A mark that is a whole scan (canvas) | The photo-only view (journal) | Lines and Words are the same pairing |

Read together, the rows suggest three axes the whole piece already has:

- **Material:** hand, type, or both (Pages, Lines, Typeface, Scan, Words, Study, Hand ↔ Font, scripts).
- **Time:** as written, revisions within a page, drafts, versions (Revisions mode, marks, Versions panel, planned version label).
- **Order:** by poem, scatter, spiral, notebook page order (arrangement row, page strip).

## Three directions, control by control

Each direction answers "where does this control live?" differently. They can combine: B for the spatial logic, C for where controls attach, A for the names.

- **A. Shared lenses:** keep two places, but both use the same Material, Time and Order controls; switching place changes only the space.
- **B. Zoom as hierarchy:** one space; the journal is the closest zoom. What you can choose depends on how far in you are.
- **C. Object-first:** a small global bar; everything else appears on the thing you tap.

| Control group | A. Shared lenses | B. Zoom as hierarchy | C. Object-first |
| --- | --- | --- | --- |
| Place (Journal / Constellation) | Stays, as a clearly different switch | Gone; zoom in to read, pinch out to return | Gone; "read" appears on a tapped page |
| Lines / Pages / Unfold | Material lens | Unfold becomes the default: depth decides | Global, rarely changed |
| Typeface, Hand ↔ Font, scripts | One Material lens: hand / type / script | Material lens, close in only | On the tapped line or page |
| By poem / Scatter / Spiral | Order lens (canvas only) | Far zoom only | Global bar |
| Whole | Action beside Order | Pinch out fully | Global bar |
| Journal mode / view (Scan, Words, Study) | Material lens | Close zoom only | On the open page |
| Revisions replay, marks toggle | Time lens: revisions | Close zoom only | On the open page |
| Versions panel, drafts | Time lens: drafts / versions | Mid zoom on a stack | On the tapped stack |
| Page strip, next / previous | Order inside the journal | Close zoom: page edges | On the open page |
| Notes (foot, end, reflections) | A layer on/off | Close zoom: marks appear | On the word, line or poem |
| Read aloud, forward / backward | Action on a poem | Close zoom | On the poem |
| Puzzle marks, revisions dig, cut-up views | Layers | Close zoom | On the page |
| Sound, sensors, participation, email | Global | Global | Global bar |
| Search, theme, info | Global | Global | Global bar |

Across all three, the global set stays small and fixed. What differs is whether the rest is organised by axis (A), by distance (B) or by object (C).

## Drawing checklist

Each sketch should answer these, so two sketches can be compared:

- [ ] What does a first-time visitor see at rest, with nothing tapped? (Your rule: the work alone.)
- [ ] What is the one gesture that reveals controls, and what appears first?
- [ ] How does each of the five kinds look different: place, setting, action, contextual, global?
- [ ] When a choice is on, how is that shown without the icon changing?
- [ ] When a press removes or adds controls, how does the eye follow the change?
- [ ] Where do contextual controls appear, and what connects them visibly to the thing that caused them?
- [ ] How is a planned feature drawn greyed out, and what does tapping it do (nothing, or a short "coming" note)?
- [ ] Which single name or icon does each collided word get (Journal, Revisions, Drafts, Versions, Hand / font, Pages / Scan)?
- [ ] Does it work one-handed at phone width (390 px) and with a mouse at desktop width?
- [ ] Where do the 25 planned features fit without the global set growing past about five items?
