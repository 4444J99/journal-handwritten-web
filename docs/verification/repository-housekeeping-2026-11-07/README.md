# Repository housekeeping closeout — 7 November 2026

Application integration is complete in both repositories. Full hosted Actions green remains **blocked by account billing**, not by failing tests. No checks were disabled or replaced with fabricated successes. Issue #111 remains the owner action. Posting local-ci statuses was also denied by integration permissions (403); the checked receipts remain explicit evidence.

## Integration and checks

Source PRs #143–#148 merged using expected head OIDs; reader PR #4 merged after matching Studio code/pin deployed. Both application main branches match their observed remotes and tested PR trees: source 093d34083d7c6207502d4e980788855e8bc26d1e; reader f164cb186f821ee63577d9ecbf61fa7e1f590d83. This subsequent documentation-only closeout does not change the tested application tree. Recheck its resulting main ref and retire its branch after merge.

All five source suites pass on accepted head 6514d8a: integrity, Python400 (1skip), Node128, Cloudflare Python68 (1skip), Cloudflare Node157. Reader9 tests pass after integration. Actual Chromium tests reproduce old failures and verify reader modes, photo pixels/bookmarks, source geometry separation, transcription/stanza preservation, modal and line keyboard behavior, source-mode guards and light/dark contrast. Independent scoped reviews approved. Cloudflare and Semgrep checks pass. The historical timeout fixture now reaps its child, preserving the whole-group-stop assertion without misclassifying terminated zombies.

## Preservation and retirement

Original inventory: source47 remote branches and reader4, no open PRs/stashes or additional worktrees. Full bundles were independently restored with all refs matching and fsck passing. Remote archive/branches-2026-11-07 tags were independently retrieved and every inventoried tip was found. Archive mappings preserve original names and OIDs, including squash-merged and superseded prototype/WIP history. Private source recovery is not copied into the public reader repository.

48 original stale branches plus7 finished integration branches are retired (55 at this application snapshot); exact-tip actions are in retirement-actions.json. Accepted changes remain on main; explicitly superseded content is not merged back over newer implementations. The sole retained source feature-like branch is playground, consumed by its active URL and synchronized with main. Reader retains main only. The documentation-only closeout branch is retired separately after merge. Temporary worktrees are removed only after clean-state checks; ignored build caches are reproducible and no external author assets were retired.

68 open source issues are deliberately retained: most are exchange records or owner/release decisions. Branch cleanup does not certify source readings, filing, physical iPhone acceptance or artistic decisions. No new poem release or snapshot-pointer publication was invoked. The staging connection to the private source repository remains disabled.

## Deployments and repeatability

Application code deployments succeeded for Studio093d340 and readerf164cb1. Their approved shell pin is a206cb90fb65ba2871713fe65ed0eb166102b221c21e6ebd968b06c156b299e0; package bytes and Studio configuration match. Subsequent documentation-only commits preserve that pin. Playground is kept current through fast-forward updates, with original history preserved in the recovery tag.

Final closeout reobserves both main refs, clean worktrees, no open PRs, surviving archive tags, active preview synchronization and deployment status. A repeated assessment on unchanged state must propose zero additional repository mutations. Full final ref/deployment observations and that second assessment are recorded in /workspace/repository-recovery/2026-11-07/closeout.json and closeout.md after this receipt merges.
