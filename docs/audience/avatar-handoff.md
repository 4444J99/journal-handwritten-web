# T06 avatar provenance and T07 production handoff

**Status: partial recovery; author arm-treatment decision and original-file recovery remain open.** This handoff uses the November 5, 2026 America/New_York review baseline and immutable source baseline `d74df372ace00c8a7544ab3b5302cb05418d672c` (tree `6d544b582b868a395a45e04cf934d1e7fd5524ca`), inspected November 6 UTC. Integration refreshed main to `fab6a82b72f23efb16278b90cdc4f7790ca55713`; the cited avatar exchanges are unchanged. It records source evidence and supplied bytes. It does not certify the supplied `v3` as the documented `v2`, approve an avatar, or authorize production/publication.

The supplied `vers_forms_profile_v3.jpg` and `preview3.png` are intact and were visually inspected. The exact documented v2, original scans, editing script and 110-pixel preview were not recovered. T07 owns production exports after source recovery and the author's D13 decision. No asset was edited, regenerated or renamed.

## 1. Sourced history and authority

| Record | What it establishes | Evidence class and limits |
| --- | --- | --- |
| [Profile-picture index](https://github.com/4444J99/journal-handwritten-web/blob/d74df372ace00c8a7544ab3b5302cb05418d672c/docs/chats/2026-11-04-profile-picture-edit.md) | November 4 chat produced a reported 1080-pixel `vers_forms_profile_v2.jpg`; removed words, recentered for the circle, and continued arms along their own angles. Source chat ID `12a3b986-e69b-40f3-9117-b2f29f099eb7`; source reviewed in the repository on November 5. | Repository evidence of historical work. The private chat was not directly accessed. Index blob `fe8ca30f0a6a2ddb7b848fc289edde5943342fa9`. |
| [Exchange 01: circle-safe crop](https://github.com/4444J99/journal-handwritten-web/blob/d74df372ace00c8a7544ab3b5302cb05418d672c/docs/chats/2026-11-04-profile-picture-edit/01-circle-safe-avatar-crop.md) | Original attachments were `FullSizeRender.jpeg` and `IMG_4824.jpeg`. Ink bounds/paper tone were measured from the latter. PIL/numpy/scipy work extended paper with synthetic matching grain and centered the ink; recorded output `vers_forms_profile.jpg`, 1080 × 1080. | Recorded implementation, not reproduced or pixel-verified here. Original marks were described as unchanged. Blob `9587370310d3b07ee4ee5e1c494330937763d67b`. |
| [Exchange 02: remove words and extend arms](https://github.com/4444J99/journal-handwritten-web/blob/d74df372ace00c8a7544ab3b5302cb05418d672c/docs/chats/2026-11-04-profile-picture-edit/02-remove-words-extend-arms.md) | The author requested word removal and arms extended like the legs, angled in a different direction. Recorded `pfp2.py` faded words, fitted arm centerlines and continued each upward at its own angle with tiled copies of the author's stroke pixels and tapered ends. Real paper sampled from a blank scan and mirror-tiled replaced v1 synthetic grain. Output was `vers_forms_profile_v2.jpg`, 1080 × 1080, with 540- and 110-pixel circular previews. | Explicit author request plus separately identified recorded implementation. Exact intended arm treatment remained unresolved. This record describes pixel sampling and script work; it does not support calling the work newly generated art. Blob `a8c2f0a805bbdc287aff06df8b825c0ebf13d3ff`. |
| [Issue #70](https://github.com/4444J99/journal-handwritten-web/issues/70) | Open; created/updated November 5 at 16:55:36 UTC; no assignees and zero comments when checked. Author must confirm own-angle arm continuation versus legs mirrored upward, and decide whether the possible slang reading is acceptable. Handle/domain checks and optional bio wording were proposals. | Live unresolved issue. Historical requests do not provide new authority to edit, publish or change accounts. |
| [Archive README](https://github.com/4444J99/journal-handwritten-web/blob/d74df372ace00c8a7544ab3b5302cb05418d672c/claude/README.md) and [merged PR #103](https://github.com/4444J99/journal-handwritten-web/pull/103) | Nontext project artifacts were intentionally archived outside Git at `/Volumes/Archive4T/Archives/versforms/claude-project-artifacts-2026-11-05/`, with `INDEX.md` and `SHA256SUMS`. PR #103 merged November 5 at 22:36:38 UTC as `04168b1f68bc4579fae245f8411b0b337d064369`. | The archive volume and its inventory were inaccessible here. PR #103 reports 28 files hash-verified before/after moving, zero failures; this handoff does not independently verify that archive claim or infer its exact avatar contents. README baseline blob `586afe02620dd8d1f5fadb9c528493be9efcc87f`. |

Earlier v1 names and methods remain history. Worded crops were superseded by the author's removal request. The later `v3` filename alone proves neither chronology relative to the recorded exchange nor which arm interpretation the author accepted.

## 2. Recovered supplied assets

| Supplied asset | Source locator | Independently observed file properties | Status |
| --- | --- | --- | --- |
| `vers_forms_profile_v3.jpg` | Session-local `project_sources/06-vers_forms_profile_v3.jpg`; source file ID `file_00000000216881f7bad78539a2f07252` | JPEG; RGB; 1080 × 1080; 269,257 bytes | Original supplied bytes preserved. Filename-labeled v3, with unverified lineage and no recorded approval. |
| `preview3.png` | Session-local `project_sources/05-preview3.png`; source file ID `file_00000000aa2881f7a2ab844c63ce1bb3` | PNG; RGB; 540 × 540; 214,060 bytes; opaque, no alpha channel | Original supplied bytes preserved. Visually similar to supplied v3; not authenticated as a v2 preview. |

SHA-256 values:

- `vers_forms_profile_v3.jpg`: `370d979bedd5779e105d7f5a85443adf22aa4fc8496fe122d3f83f8d6018185e`
- `preview3.png`: `88663f21fd47fa13c189c88844541deb52335eba8760295066b26d8913550b02`

Visual inspection found a black-marker human figure on cream paper, with a horizontal right-pointing arrow through the figure, raised arms, legs spreading downward and an outline head. No words are visible. The preview shows the cream field as a circle with white corners. Extremities fit within that field, with a lower tip near the edge. These are observations of available bytes, not acceptance of the drawing, correspondence to the inaccessible v2, or evidence of present account use. The record's concern about the faint head at small size remains a T07 QA item.

The session-local paths above are recovery hints, not repository files or durable delivery URLs. The source file IDs and checksums are the stable matching references. See [machine-readable inventory](avatar-manifest.json). T06 preserves the repository's established policy of keeping nontext originals outside Git.

## 3. Exact recovery gaps

| Missing or unauthenticated item | Last documented locator | Required recovery input |
| --- | --- | --- |
| `vers_forms_profile_v2.jpg`, 1080 × 1080 | Profile-picture chat `12a3b986-e69b-40f3-9117-b2f29f099eb7`, November 4, exchange 02; chat-only output | Exact original output or archived copy, provenance and checksum. |
| `vers_forms_profile.jpg`, 1080 × 1080 | Same chat, exchange 01; chat-only output | Exact prior output if needed for historical comparison. |
| `FullSizeRender.jpeg` | Same chat, original attachment in exchange 01 | Original attachment bytes, filename and embedded metadata. |
| `IMG_4824.jpeg` | Same chat, original attachment in exchange 01 | Original attachment bytes; record identifies this as the source for measured bounds/paper tone. |
| `pfp2.py` | Same chat, exchange 02 | Exact script and environment/dependency notes if retained. If unavailable, record that gap rather than recreate it silently. |
| Documented 540-pixel v2 circle preview; filename not preserved in accessible text | Same chat, exchange 02 | Exact preview and source linkage. `preview3.png` does not establish this identity. |
| Documented 110-pixel v2 circle preview; filename not preserved in accessible text | Same chat, exchange 02 | Exact preview and source linkage. No corresponding supplied file was recovered. |
| Archive `INDEX.md` and `SHA256SUMS` | `/Volumes/Archive4T/Archives/versforms/claude-project-artifacts-2026-11-05/` | Read-only relevant inventory/checksum records and any matching originals. Their existence is documented; their contents were not seen. |

The private chat locator is [the recorded profile-picture chat](https://claude.ai/chat/12a3b986-e69b-40f3-9117-b2f29f099eb7). That link is a recovery locator, not a claim that its present contents were accessed.

Recovery checks were bounded. Filename searches covered supplied sources and accessible scratch/checkouts. Member-name searches in the two supplied journal ZIPs (384 and 254 entries) found no matching profile/preview/pfp/FullSizeRender/IMG_4824/avatar/media-kit filename; their images were not exhaustively inspected. Exact Library title queries for the five named originals/output/script returned no exact matches. The provider warned that supplemental title candidates were first-page only. These results establish an access gap in inspected sources, not global absence or deletion.

## 4. Finite author decisions

### D13 — arm treatment and exact avatar source

Owner: author. Status: unresolved. T07 implements only the chosen, concretely identified direction.

| Actionable option | Required input | Consequence |
| --- | --- | --- |
| Recover/review documented v2 and approve its own-angle arm continuation. | Exact v2 bytes or authenticated archive copy, author review of square/circle/small previews, explicit source-hash selection. | T07 can prepare private exports from that approved source; it must not relabel supplied v3 as v2. |
| Request an alternate with the legs' spread mirrored upward. | Recovered originals, concrete author instructions resolving the geometry, and a T07 production assignment. | Creates a new derivative that needs its own version, source hashes and author acceptance. The historical request alone does not approve it. |
| Defer changes and retain the current avatar. | Identify the exact current asset/account state if a production handoff is needed. | No replacement production is necessary until the author reopens the choice. No available file is assumed to be the current avatar. |

If the author instead identifies the supplied v3 as the desired existing source, record that explicit selection against its checksum within D13. Its filename is not a substitute for that decision. No spend is required for any review option; production resources and account changes remain outside this handoff.

### D14 — slang reading and optional explanatory copy

Owner: author. The record raises a possible slang reading of `vers.forms` and offers optional clarification through a bio. This remains an author judgment. No new naming round, bio, explanation, caption or reply has been written. Any optional wording must be supplied by the author.

## 5. T07 production interface

T06 supplies this evidence record and byte inventory. T07 owns source recovery, production exports, crop/legibility QA and the media-kit package. Before production, T07 needs the approved exact source, D13's decision, original scans or an explicit record that they cannot be recovered, and the intended private export destinations. Preserve original bytes and filenames; attach derivation history and hashes to every derivative.

Reuse of the documented 1080 × 1080 square, 540-pixel circle preview and 110-pixel small preview is a practical **proposed QA set**, not a claim about current platform requirements or an approved production specification. T07 should inspect the faint head, arm tips, arrow and legs at both circular sizes, check edge clearance, and record whether padding/crop/color/transparency changed. The supplied preview has white corners and no transparency. No T06 production exports were created.

[The November 3 post/kit mockup exchange](https://github.com/4444J99/journal-handwritten-web/blob/d74df372ace00c8a7544ab3b5302cb05418d672c/docs/chats/2026-11-03-widget-photo-page-format/02-post-and-kit-mockups.md) is historical input, with source chat `7c08a977-0f69-43ad-acb8-bf55165eb0e1`, canvas `9YjDdZ6pSUdA21V164fr1y`, and repository blob `bfba464be6335420a84969984ad5fd080d6279ed`. It describes 13 screenshot-derived widget tiles and six layout boards. It expressly leaves rendering inspection, numbering, Series/Reserve auditing and device album behavior open. The pages were chosen by crop suitability, not release clearance. Real production requires scans and cleared page selection. This record is not an approved, production-ready T07 media kit, and no current Apple behavior is inferred from it.

T07's eventual handoff should provide exact asset paths, formats, dimensions, hashes, source lineage, author selection/approval reference, and privately reviewed crop previews. Poem scans and kit contents must use T03's clearance contract; T06/T07 must not create independent release logic. Existing ownership stays intact, and all identity/source labels remain versforms. ETCETER4 is a separate project; historical filenames are provenance, not authority to combine projects.

## 6. Consume the T03 contract

[T03 draft PR #119](https://github.com/4444J99/journal-handwritten-web/pull/119) at head `8d16284ba8b80f18398d08b8de931d8812f30429` supplies [the proposed `versforms.release-clearance.v1` contract](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/docs/releases/release-clearance-contract.md). It is a proposed interface, not evidence of a cleared release. Its current packet is awaiting author/evidence; `may_publish` and `may_schedule_external_actions` are false.

For any future cleared release, T07's exact output manifest must feed that contract, including source/output hashes, visible identity, scans and any neighbor exposure. Source-linked author clearance must cover the exact manifest. A Series classification, filed/registered status, build, schedule or “Mark posted” action does not grant publication authority. Relevant content/version/review/source/scan/output changes invalidate clearance under T03. Publishing also needs separate current execution authorization. This avatar handoff neither duplicates those gates nor makes a release selection.

## 7. Dispositions and remaining limits

- **#70 — unresolved, with preparation complete:** source evidence, available-file inventory and D13/D14 are consolidated. Arm selection and exact original recovery remain open. No issue was closed or externally commented on.
- **#69 — historical completed crop:** retain its original crop and method in the history; do not treat it as approval of later arm changes.
- **#67 — T07 dependency:** historical kit mockups are source material, with explicit clearance and QA gaps. This handoff does not certify production assets; #67 is contextual evidence, outside the eleven scoped issues.

The shared context packet `2026-10-16-v1.1`, projection `2026-10-16-v1.1-r2`, in private project `g-p-6a10bcb4ada4819194e881431212101a` was inaccessible. No claim here is attributed to unseen packet contents. No images were generated or modified, originals were preserved byte-for-byte, and no accounts, publications, messages, spending or issue states changed.
