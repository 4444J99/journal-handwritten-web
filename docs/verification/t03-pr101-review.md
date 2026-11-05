# T03 review of PR #101

Observed November 5, 2026. Dependency: [PR #101](https://github.com/4444J99/journal-handwritten-web/pull/101), open and unmerged, head `5d111c13764655312c32ddf1b55390198bc7f70c`. T03 preserves this posting implementation. No successor posting PR was observed in the refreshed repository list. PR #97 is reader verification; PR #102 is a private prototype; neither replaces the posting path.

## Original-baseline findings reconciled

| Existing review | Exact evidence and disposition |
|---|---|
| [Comment 4486446890](https://github.com/4444J99/journal-handwritten-web/pull/101#discussion_r4486446890), withheld substring matching an allowed longer line | The current `leak_check` retains structural exclusion and masks occurrences within authorized longer readings before substring searching. The regression coverage passes. The thread is still unresolved and marked outdated; T03 did not change its state. |
| [Comment 4486446898](https://github.com/4444J99/journal-handwritten-web/pull/101#discussion_r4486446898), origin lookalike hosts/paths | The current `remote_is_public_repo` parses URL and SCP forms, requires github.com, checks scheme/port, disallows query/fragment and matches the repository path. The regression coverage passes. The thread remains unresolved/outdated. |

An independent review agent ran all 92 tests in `tests/test_post_poem.py` against that exact dependency: **OK, one skipped**, 43.647 seconds. The skip was `test_python_without_fonttools_is_reported`: the available system Python already has fontTools, so this specific absence simulation could not run. The other font tests ran. [Full log](t03-2026-11-05/pr101-posting-tests.txt).

The root worker independently read both corrected functions, their related test outcomes, `shared_scan`, `check_output` and the public PR rendering code. Root's separate complete 104-test run includes the seven preparation tests and five existing local-CI tests; its immutable-revision receipt is separate from the agent's 92-test result.

## Boundaries still requiring the release contract

- `--accept-shared-scan` is an operator-supplied exception. It contains no identity, dated author decision or binding to the exact image bytes. The generated PR actually lists author sign-off under **Not verified**; that wording is not evidence that sign-off occurred. T03 supplies no exception and does not resolve the author's policy question.
- `shared_scan` can allow another version of the same piece on a facing page, or writing from an already-public piece. Public piece membership does not clear every version. T03's exposure audit checks all catalogued writing outside the selected version's blocks, including the same piece's other drafts.
- Existing output checks prove structural/text exclusion, font parsing/naming, title, and noindex. Whole scans and page atlas rectangles can still show withheld handwriting. The bounded packet adds exact file allowlisting, image-source hashes, metadata inventory and byte-for-byte atlas reconstruction, then maps the catalogued writing on every copied page/spread.
- Those technical checks establish which source pixels were bundled and whether catalogued withheld blocks are present. They cannot identify unknown marginalia or establish author consent. Root visually inspected the actual diary1 and diary62a scans; the packet keeps the author review gate and catalogue limitation explicit.

## T03 helper review

The independent reviewer found no material flaw blocking the current preserved-data p001 packet. The helper calls the existing posting dry run without fabricated records or override flags, refuses a nonempty first-release whitelist, inventories the exact output, preserves input hashes and always records `release_clearance: false`.

The current eight-file preview excludes the second version, its page and p126. The deliberate all-versions comparison fails image exclusion at diary62a blocks 3 and 4. A minor future-reuse issue in the report's left scan was corrected before code freeze: it now uses the actual selected preview page and version IDs. The browser verifier also derives its omitted-image probe from the input/output inventories.

No original posting file was modified, no review thread was resolved, and no public repository, deployment, filing or release was performed. Font metadata, information-panel wording, exact version/scan clearance, filing confirmation/evidence, Site/social semantics and physical-phone acceptance remain explicit gates.


## Late refresh: e5ae157e

Before handoff, PR #101 advanced to `e5ae157ef556690e73047e30225cad61c5484cf9` (tree `c4c4fb0479b5be9563258a85b58a8458fe1d1f8a`). Root and the independent reviewer read the updated builder/posting/tests/docs and refreshed review threads. T03 preserved the earlier packet under `release/packets/2026-11-05-t03-baseline` and created a new isolated branch on this dependency; no old branch or peer work was overwritten.

The newer loader refuses an export with no release records. The preserved export is authentic (38 reviews, no pool/batch records), so the actual current posting dry run exits **3** before the ordinary gates. Private inspection now calls the existing studio `import_export.scan` reader, validates every document, and creates no SQL or synthetic pool/filing record. Its separate evaluation of the existing gate functions still finds 38 reviewed lines, no Series classification and no batch. The posting command's refusal is retained without an override.

The newer builder strips unpublished line slots/geometry and blocks quotation corrections; scan detection includes whole-spread scans and byte-identical scan twins. It also hardens pool/export/batch/URL/workdir validation, isolates public commits in worktrees, and delays atomic whitelist writes until the public push and PR succeed. T03 takes these changes intact rather than implementing competing posting logic. The earlier URL review is fixed more strictly now: current public repository URLs must be HTTPS, not SSH.

A new active review, [discussion 4487062599](https://github.com/4444J99/journal-handwritten-web/pull/101#discussion_r4487062599), identifies multiple configured push destinations: `get-url --push` checks only the first, while a push can send to all. Root and the independent reviewer confirmed the code lacks `--all` at this snapshot. This is an unresolved gate before a real posting run. The preparation path never calls public-clone commit/push code.

The latest documentation also makes an existing exposure explicit: the unchanged reader HTML retains PAL/HF identifiers and block relationships for withheld pages. T03 now inventories those literals and marks **metadata exclusion and complete technical exclusion as failed**, separately from the passing text/version-data/image exclusion checks. No blanket metadata-exclusion or release-readiness claim is made. Resolve through an explicit author rule or a reviewed T04/builder change and retest.

The independent review's 92-test pass remains tied to `5d111c1`. Its late follow-up was a read-only delta/loader/exposure probe, not a rerun of the enlarged suite. Current runtime test results are in the separate current-revision receipt.
