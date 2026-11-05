# T03 current release-preparation verification — November 5, 2026

**The private packet is prepared. Text/version-data and image exclusion pass; complete exclusion fails because reader metadata remains. Release is blocked.** The actual posting command exits 3 on the authentic export's empty release collection. No pool/filing record, author approval or release state was invented.

## Tested identities and late-head reconciliation

| Subject | Identity |
|---|---|
| Current preparation code | `6d1ff59fb6763f80828478e7819d9d879dd700e3` |
| Current preparation tree | `ce5a37af26a1eedd64ffa2a089440c9d886c467b` |
| Posting dependency, PR #101 | `e5ae157ef556690e73047e30225cad61c5484cf9` |
| Current packet | `release/packets/2026-11-05-t03-current/` |
| Earlier preparation, retained as history | `e0177fa8a53ee41eda31a90253fbab3cc798556e`, on dependency `5d111c13764655312c32ddf1b55390198bc7f70c` |
| Earlier packet | `release/packets/2026-11-05-t03-baseline/` |
| Latest independently compared main | `d74df372ace00c8a7544ab3b5302cb05418d672c` (PR #118 verifier cleanup) |

The current packet was generated after its code commit existed. `packet.json` binds that revision to each tool/input SHA-256. Later evidence/docs commits do not change those tested code bytes. PR #101 advanced while this task ran; root preserved the first rehearsal, independently inspected the delta and reviews, materialized the exact new commit/tree, and created a new isolated branch without rewriting the earlier branch.

The new posting loader requires at least one release document. The preserved export genuinely has 38 reviews and no release documents, so the real command now stops at exit 3 before evaluating normal gates. The private helper uses the studio's existing read-only `import_export.scan` validator; it generates no SQL and fabricates no rows. Separate calls to the existing gate functions find 38 reviewed lines, no Series classification and no batch. These private evaluations do not convert the CLI refusal into a pass.

At the final 23:33:42 UTC refresh, main advanced from 3eadec6 to d74df37 through PR #118. The three-file delta fixes the shared CDP verifier's browser cleanup/test assumptions and corrects the session history for issue #115. It changes no release, site, studio, export or CLAUDE.md file. T03's bounded browser verifier uses Playwright. The delta was inspected but is not included in, or claimed tested by, this stack; PR #101 remains open at the exact tested e5ae157 head.

## Actual check results

| Check | Result and scope |
|---|---|
| Required `tools/check.py` | Exit 0; 509 references, zero missing, 511 checksums. Current dependency includes the stricter manifest check. No manifest rewrite. |
| Full Python suite at current preparation commit | **151 tests, OK, one conditional skip, 78.407 seconds.** The system Python has fontTools, so its absence could not be simulated in one test. Other font checks ran. |
| Current real posting dry run | **Exit 3**, preserved empty-release export rejected. No override flags or public clone supplied. |
| Bounded content exclusion | **Pass** for structural/text/version-data, exact file inventory, catalogued image exposure, font/title/noindex checks and atlas reconstruction. |
| Reader metadata exclusion | **Fail:** 13 withheld-page identifiers and PAL/HF block structure remain in index.html. Complete technical exclusion is false. |
| Reproducibility | Two independently generated current previews have identical file hashes. All eight current preview files are also byte-identical to the earlier bounded preview. The stronger audit changes the interpretation of those bytes. |
| Current browser acceptance | Chromium 153.0.8010.0, desktop 1280×900 and touch/phone-width emulation 390×844: reader/font load, title/noindex, hidden info at rest, info opening, Journal rendering, no errors/failed requests, no horizontal overflow, and omitted diary62a image 404 probes pass. |
| Studio database acceptance | **12 checks pass** using disposable local D1, real studio/adapter/API and existing test helpers. Invalid URL and first tap write nothing; second tap persists; Site/Instagram writes append and survive fresh reloads. Narrow desktop viewport only. |

Evidence: [check summary](t03-2026-11-05/check-summary.json), [151-test log](t03-2026-11-05/python-tests-6d1ff59.txt), [current browser receipt](t03-2026-11-05/browser-results.json), [studio receipt](t03-2026-11-05/studio/acceptance.json), [studio procedure](t03-studio-acceptance.md), [PR #101 review](t03-pr101-review.md).

A final independent review corrected earlier report prose: diary62a has 16 reviewed lines, comprising 11 confirmed and five corrected; diary1 has 22 confirmed lines. Issue #113's five-correction statement is accurate. The report now derives its aggregate review counts from the audit. The preserved earlier packet retains its historical wording, which must not be used as the current count. This correction does not change the proposed public bytes.

The independent review's 92-test run and root's earlier 104-test run apply to the original baseline only. Their records remain available. An interim 151-test run at e40f1a0 is also retained in python-tests-e40f1a0.txt; the current run is the 151-test receipt at 6d1ff59, after the review-count correction. The baseline's original technical-pass field covered its original check set; it did not check PAL/HF metadata. The same HTML bytes contained that metadata then, so the current audit supersedes any inference of complete exclusion. Existing ResourceWarnings about unused atlas file handles remain minor inherited findings; no output/hash mismatch resulted.

## Exact public-output inventory and remaining exposure

The proposed current `preview/` is **eight files, 595,130 bytes**, containing one piece (`p001`), one version (`p001-diary1-0`) and one page (`diary1`): index.html, _headers, data/j.json, three diary1 page tiers, and two rebuilt atlas files. No spread, hand-font plate, source export, review queue or comparison image is bundled in preview/.

The [content exclusion complement](t03-2026-11-05/exclusion-complement.json) lists 125 pieces, 155 versions and 122 pages omitted from the output data, plus their 366 absent page-tier paths. Copied image hashes equal the source hashes. Both atlases reconstruct byte-for-byte from diary1's declared rectangle and white padding. The five JPEGs have no EXIF tags. Decoded font name/description records remain available in the private packet for author review.

The HTML nevertheless contains these **13 withheld page IDs**: diary13, diary13a, diary14, diary14a, diary21a, diary26, diary3, diary53, diary53a, diary54, diary63, diary8 and diary8a. The literal PAL/HF structures are fully recorded in packet.json and the complement. They refer to pages carrying p004, p012, p020, p032, p040, p068, p096 and p097. No transcript/scan for those works is bundled, but the identifiers and relationships themselves remain exposed. An author ruling or a reviewed T04/builder change is required; no clearance is inferred.

The private alternative-version comparison deliberately includes diary62a and fails image exclusion at p126 blocks 3 and 4. That scan belongs to the private packet, not its proposed preview/. Root visually inspected both actual scans and the final preview screenshots. This proves which source pixels were bundled and maps catalogued withheld writing; it does not certify unknown marginalia, author consent or a work's never-online history.

## Acceptance limits and integration gates

- Physical phone/WebKit acceptance remains with T04. The release browser run uses touch emulation; the 12-check studio run uses desktop Chromium at 390px. Neither is a physical-phone test.
- The hosted HTTP header was not exercised; noindex meta and _headers output bytes were checked locally.
- Info retains empty scan provenance fields and the global unchecked-transcription sentence. The font carries author/source description metadata. These remain explicit author questions.
- Diary1 block 2 has four transcript lines but three source line boxes; its fourth review box is null. T02/T04 must reconcile crop/highlight alignment. No coordinates or text were guessed.
- The studio receipt's actual tested revision is 5d111c1. All studio/studio-cf blobs are identical at e5ae157e; root independently checked the receipt source hashes. This is equivalence evidence, not a relabeled new run or a live-D1 claim.
- Mark posted writes social even for the Site address; the Site shortcut writes site and leaves Calendar unposted. Both map to false UI classifications; no pub boolean is stored. Confirm semantics before downstream automation.
- The new active multiple-push-URL review (discussion 4487062599) remains a non-dry-run posting gate at the tested dependency. T03 exercises no public push path.

## Preservation and closeout scope

Current private branch: `t03/release-packet-2026-11-05-current`, stacked on `post-poem-gates`. Original branch `t03/release-packet-2026-11-05` is retained at e0177fa as a preservation reference. No branch retirement, pruning, force push or history rewrite was attempted. Original PR #101 posting/build/font files are unchanged relative to the current dependency; T03 adds inspection and evidence around them.

Site, studio, preserved exports and the public whitelist retain their recorded input hashes. Active peer checkouts and uncommitted work were not edited. Both plan copies have additive dated updates; historical text remains. The local exact commits/trees were reconstructed through the GitHub connector because direct authenticated fetch was unavailable. Earlier history is shallow; no complete-history or ancestry-cleanup claim is made. Remote final branch/PR parity is checked at handoff.

The latest repository session record reports earlier scan exposure elsewhere and live deployment activity by another session. T03 did not independently verify those external surfaces or act on them. This packet proves prospective output properties only. The private shared context packet/projection remains inaccessible. No release, merge, deploy, filing, issue closure, account operation, expenditure or external message was performed by T03.
