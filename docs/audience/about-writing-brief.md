# About versforms — author writing brief

Prepared November 6, 2026 (America/New_York) in response to the author's request for an explanation of what the project is. This is a private writing brief, not public copy. The author supplies the creative and interpretive text.

## A useful first draft

Aim for roughly 150–250 words, in three short paragraphs. The length is an editorial suggestion, not a requirement. A voice note or rough answers are enough to begin.

1. **What is this?** What do you call versforms, and what should someone understand after the first two sentences?
2. **Why these pages, now?** Where did the notebooks come from, and why are you returning to that writing? What connects the writer then with the writer now?
3. **Why this form?** What matters to you about the handwriting, visible revisions, arrangements and the name? What should a visitor be free to notice or do?

An optional final sentence can describe where the work is going. Include a fixed cadence, participation mechanism or release promise only when you want to make that commitment publicly.

## Keep orientation separate from the statement

The menu provides separate **About** and **How to explore** destinations. About is the place for your account of the work; How to explore explains the actual controls. Technical help can be maintained with the implementation. A visitor should be able to use the reader without having to interpret the artist statement as instructions.

Implementation contract: `#b-info` opens About (`#infop`); `#b-help` opens How to explore (`#helpp`). The About panel retains the existing source/transcription information and the author's supplied crown. Its `#about-author` section starts **hidden and genuinely empty**, without a placeholder, inferred biography or generated statement. These are the implementation targets; browser verification is recorded separately in the session closeout.

## Insert the author's copy

1. Receive the exact paragraphs the author wants presented. Rough notes or a voice note can help him draft, but are not automatically approved public copy.
2. Put only those supplied paragraphs inside `#about-author`, using text nodes or correctly escaped paragraph markup. Preserve the author's words, punctuation and intended paragraph breaks; make creative edits only on his direction.
3. Remove the section's `hidden` attribute when it contains the supplied, approved text. Leave it empty and hidden until then. Keep this brief, source notes and internal implementation comments out of visible presentation text.
4. Check the rendered About panel and its keyboard/touch return path. Rebuild the candidate engine so the source reader and generated artifact agree. Record the exact output and use the existing engine review and matching Studio shell-pin process for activation.

The practical help remains in `#helpp`; it should describe the verified controls without adding an interpretation of the poems. Supplying About text does not itself select or clear any poem for publication.

## Evidence available to draw on

| Subject | Dated source and limits |
| --- | --- |
| Identity | [The identity record](identity-status.md), `T06-ID-01`, records **vers.forms**, public title **versforms**, and font **ajp-scribbles**. The font name is not the name of the work. |
| Meaning of the name | That record attributes “forms taking shape versus one another” to the author, citing I49 / X49 (October 31, 2026). This is a recorded phrase to revisit, not a completed public description. The underlying exchange was not independently retrieved for this brief. |
| Source | The accessible October 28, 2026 plan describes journal material circa 2014–2015 and scans made in September 2015. Its source section is retained in [the repository plan](../plan.md#source). Archive counts are background and need not lead the About page. |
| Intended series | The October 28 plan records a goal of 100 full poems using edited journal work and new writing, with revisions retained. This does not mean 100 finished or published poems exist. The 123 scanned pages and 126 catalog entries are different counts. |
| Cadence history | October 28 records a weekly cadence as a leaning. `T06-ID-01` later records one poem per week as an author decision, citing X41 (October 31). Neither source establishes a current first-post date or completed releases. Reconfirm any schedule wording the author wants to put in his About text. |
| Authorship and publication | [CLAUDE.md](../../CLAUDE.md) reserves creative and interpretive presentation text to the author. Earlier ETCETER4 labels are historical; this project is distinct from the author's music. The private archive and public posted-poem output remain separate. |

## Source limits

The attached `15-plan3.md` is explicitly dated October 28, 2026; its source and series passages were read directly. The local repository snapshot was supplied from inspected private main `9c0e9c565fb9d7bef3a68b21faa744010a401f60`; this local folder is not a Git checkout. The identity record was read directly, but its linked source register and individual historical exchanges were unavailable in this snapshot. No complete author-written About statement was verified among the inspected material.

The original October 16 private memory packet (`2026-10-16-v1.1`, sanitized `2026-10-16-v1.1-r2`) in private project `g-p-6a10bcb4ada4819194e881431212101a` was inaccessible: `interpretation.md`, `cloud-master-context.md` and `cloud-source-ledger.json` were not retrieved. No unseen fact or approval is attributed to them. Recommendations in later advisory documents remain recommendations; historical approvals do not authorize new publication.
