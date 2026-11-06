# Posting hardening completion — November 6, 2026

## Produced

Resumed the author's request to complete the interrupted posting-script hardening in [issue #123](https://github.com/4444J99/journal-handwritten-web/issues/123). The supplied handoff described unfinished work at `c78e903ac3c3589437c302d7b7cfee73dad85561`. A fresh GitHub read found that [PR #131](https://github.com/4444J99/journal-handwritten-web/pull/131) had already merged accepted head `7d03ac7715a7ee4d2ca3f3f4d569498633c00e25` as `7371dc394403fbcf09fd32bab563f1eb62ff3684` at 2026-11-06T11:00:59-05:00. This follow-up builds on current main `ef3d263c455788c769547df9e1e6010a54b7719a`, not on the stale WIP tree.

The existing posting suite passed on that main revision (161 tests, one environment-specific skip), but local adversarial fixtures reproduced remaining problems. In particular, inherited `GIT_CONFIG` could hide a second push URL from validation and a second disposable bare repository received the posting branch; failed worktree creation could delete a pre-existing branch. Additional fixtures exposed omitted Git environment isolation, persistent tag-setting mutation, incomplete mirror parsing, an empty push URL/refspec, missing whole-spread identity, credential disclosure and unpublished facing-page identifiers in PR warnings.

The repair keeps enforcement in `tools/post_poem.py`: one sanitized environment per Git subprocess, complete effective URL enumeration and identity checks, native Git boolean validation, explicit `--no-follow-tags`, cleanup restricted to the branch created by this invocation, and exact committed-byte verification. The script preserves the caller's environment and clone configuration. Explicit whole-spread records need an identifiable facing page; ordinary pages without spread metadata retain their existing behavior. Private console diagnostics remain available while the public PR text omits withheld page/line identifiers and credentials.

Added `tests/test_post_poem_isolation.py` with 13 regression/compatibility tests and updated two existing assertions to match the explicit push command and accurate mirror-check name. The existing filename, Reserve/Archive, stale-review, byte-comparison, leak-overlap and release-list timing protections remain in force. `docs/posting.md` now describes the actual dry-run, failure, Git and metadata behavior. The chat index's pre-existing conflict markers were removed while preserving every distinct prior chat row and the later status for its duplicated local-session row.

## Author decisions

The author said **"complete"** in response to the unfinished hardening handoff. This authorizes completing the fixes, tests and follow-up PR. The handoff's review-before-merge boundary remains: this session does not merge, publish a poem, deploy a site, change a release whitelist, or choose editorial/filing/metadata policy.

The shared packet version is `2026-10-16-v1.1`, sanitized projection `2026-10-16-v1.1-r2`. Its `interpretation.md`, `cloud-master-context.md` and individual `cloud-source-ledger.json` records in private project `g-p-6a10bcb4ada4819194e881431212101a` were inaccessible. The current request, supplied handoff and accessible live repository are the evidence here; unseen packet text and historical approvals are not treated as new authority.

## Plan / next steps

Review the follow-up PR against #123, then use the repository's normal author-controlled integration process. Keep #123 open until its repaired implementation is integrated. Public-release clearance, actual poem selection, filing decisions and device acceptance remain separate author work.

## Status

Implementation and bounded verification are recorded in the associated PR's verification receipt, including the final full head/tree identifiers, exact commands and independent review result. The intended end state for this session is an open, tested follow-up PR; default-branch integration is deliberately outside that end state.

The candidate's posting suite completed **174 tests: 173 passed, one expected skip**. The skipped test tries to simulate a Python without `fontTools`, which is installed in this runtime; actual font encode/decode tests and explicit unavailable-font tests ran. All **7 release-packet tests** passed. Python compilation and `git diff --check` passed, and `tools/check.py` verified **509 references, zero missing files and 518 manifest entries**. `fontTools`, Pillow and Brotli were available during the font-dependent tests.

Commands: `python3 -m py_compile tools/post_poem.py tests/test_post_poem.py tests/test_post_poem_isolation.py`; `python3 -m unittest discover -s tests -p 'test_post_poem*.py' -v`; `python3 -m unittest discover -s tests -p test_release_packet.py -v`; `python3 tools/check.py`; `git diff --check`. The font interpreter was selected with `VERSFORMS_FONT_PYTHON`; temporary dependency paths are local test setup, not repository requirements.

### Verification and lifecycle contract

- **Identity and inventory:** private source repository `4444J99/journal-handwritten-web`; observed main `ef3d263c455788c769547df9e1e6010a54b7719a`, tree `46bbe75e24a1098a996da6b7dc3c23dd67b09215`. A separate local checkout was reconstructed from authenticated GitHub objects and existing exact local objects; the tree and signed commit hashes were verified. It is a deliberately shallow snapshot, not a complete-history archive. Other workers' worktrees were read only and left unchanged.
- **Scope and preservation:** source/tests/runbook/session-log changes only. The original remote `post-poem-hardening-wip` was freshly observed at `c78e903ac3c3589437c302d7b7cfee73dad85561` and retained. PR #131 and its lineage remain unchanged. No repository, branch, worktree or source artifact is retired by this follow-up.
- **Ordered checks:** Python compilation and diff whitespace; the original vulnerability triggers plus alternate Git environment, URL, mirror and credential forms; legitimate publication fixtures, the original posting suite, its direct release-packet consumer and `python3 tools/check.py`. All publication exercises use synthetic text, disposable local remotes and a fake `gh`; no successful hosted posting or deployment is claimed.
- **Publication parity:** verify the follow-up branch's remote head and root tree against the tested local content, and record the exact OIDs in the PR body. No force push or update to main is required.
- **Post-integration parity:** not required here because the authorized end state is a follow-up PR. The repair is not described as integrated until a later independently observed merge.
- **Residuals and repeatability:** preserve the WIP ref and open issue until review/integration. Once the follow-up head and PR are verified, the same scoped reconciliation requires no further repository mutation. Real-host publication, deployment, unrelated tranche work and whole-repository/browser acceptance are outside this verification.
