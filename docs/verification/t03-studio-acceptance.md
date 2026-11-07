# T03 studio database acceptance and integrator handoff — 2026-11-05

**Result: 12 local checks passed, exit 0. This is technical acceptance of the existing storage path, not a release clearance or author decision.** No studio/backend source was modified. No live database, account, publication, filing or registration was touched.

## Tested identity

- Immutable source: `5d111c13764655312c32ddf1b55390198bc7f70c` (PR #101 head, archived from the T03 checkout before testing).
- Runner: `verify-release-studio.mjs`, SHA-256 `1fd5bc239c10423521ae2f841aefcc3c54928f0311be1486cb2a0833295fc0cb`.
- Run: `2026-11-05T23:01:15.450Z` to `2026-11-05T23:01:23.788Z`.
- Browser: Chromium `153.0.8010.0`; Node `v24.22.1`; Playwright `1.62.1`; `linux`.
- Exact application hashes and the synthetic persisted records are in [acceptance.json](t03-2026-11-05/studio/acceptance.json).
- Private screenshots: [Calendar screenshot](t03-2026-11-05/studio/calendar-390px.png) and [Exposure screenshot](t03-2026-11-05/studio/exposure-390px.png). These show existing first-line labels and synthetic state. They are private test evidence, not public release assets.
- Both screenshots were visually inspected in the first passing run. The final parameterized rerun exercised the same 390 × 844 viewport and passed the same checks. This is desktop Chromium at a narrow viewport; neither touch emulation nor a physical-phone test is claimed.

The first prototype completed its write/read/reload checks and then failed in the harness while trying to access the page's private `EXPO_PUB` binding. The application did not fail. The corrected probe reads the committed enum and checks the rendered absence of publication badges. The initial failed probe receipt remains in the task scratch evidence; the committed receipt is the fresh final run. The final result is the fresh-state parameterized run identified above.

## Reproduction

Create a clean source snapshot at the stated revision, then build its private studio assets with the existing builder:

```sh
python3 /absolute/immutable-source/studio-cf/build_dist.py
NODE_PATH=/absolute/installed/node_modules node tools/verify-release-studio.mjs --source-root /absolute/immutable-source --scratch-root /absolute/new-empty-test-directory --wrangler /absolute/installed/wrangler --chromium /absolute/installed/chromium --revision 5d111c13764655312c32ddf1b55390198bc7f70c
```

The runner accepts only explicit source, scratch, tool and revision inputs. It refuses a nonempty scratch root, imports the repository's existing JWT/Pages/D1 helpers, sets local persistence, creates throwaway loopback-only Access credentials and uses the real studio, adapter and API. It installs no dependencies. All API writes are to the local simulator. The imported Pages helper starts `wrangler pages dev` and initializes D1 with `--local`; no remote command is run. The result binds the supplied source revision to hashes of the tested application files and the runner. Its fixture pool assignments and `as-posted` choice are marked `T03 LOCAL ONLY; not author approval/decision` in the disposable database.

Executed final command:

```sh
NODE_PATH=/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules node /workspace/scratch/d5c1b1e5f42b/studio-acceptance/verify-release-studio.mjs --source-root /workspace/scratch/d5c1b1e5f42b/studio-acceptance/source --scratch-root /workspace/scratch/d5c1b1e5f42b/studio-acceptance/reproducible-run --wrangler /workspace/scratch/8216ae450607/t01-runtime/node_modules/.bin/wrangler --chromium /workspace/scratch/1fc151f82b99/browser-runtime/chromium --revision 5d111c13764655312c32ddf1b55390198bc7f70c
```

## Observed behavior

| Check | Result |
|---|---|
| Owner connection | Real adapter subscribes to disposable D1 and shows Synced. |
| Invalid Mark posted URL | Rejected before arming; collection revision unchanged. |
| First unready tap | Arms the confirmation; collection revision unchanged. |
| Second unready tap | Persists one event with type `social`, where `versforms.pages.dev`, account `vers.forms`, version `final`; fixture as-posted numbering assigns 1. |
| Reload after Mark posted | One event remains; Calendar displays posted; Mark posted button is absent. This is reload/visible-button duplicate prevention, not a concurrent-write/idempotency guarantee. |
| Site shortcut | Writes `type: site`, `where: versforms.pages.dev`, version `scan`; empty account omitted. |
| Site-only reload | Event persists, but Calendar remains unposted. |
| Instagram shortcut | Selects `social`, `Instagram`, `vers.forms`; manually editing Where clears its pressed state. |
| Append Instagram | Existing Site event retained; social/draft event appended. |
| Fresh reload | All three events read back through the actual API/adapter. Final release collection revision is 5: two fixture seeds plus three UI writes. |
| Publication display | Source enum maps Site and social to `false`; none of these events renders a copyright-published badge. There is no publication boolean persisted on these records. |
| Narrow viewport | 390px viewport, document and body widths are all 390px; no document horizontal overflow. |

**Semantic gate remains unresolved.** The default site-address Mark posted path writes `social`; the Site shortcut writes `site`; Calendar and the Posted counter treat only `social` as posted. Both event types share the same false UI publication classification. This is tested implementation behavior, not independent legal analysis or confirmation that the author intends that categorization. Do not treat the false flag as permission to release, submission eligibility, or proof of unpublished status. Do not use the distinction to drive downstream automation until its intended meaning is confirmed.

The current UI deliberately allows an unready record to be logged after a second tap. This test proves that path; it creates no verified lines, preparation completion, filed batch, filing receipt or public whitelist. Studio event logging must remain separate from PR #101's public release gates.

## Integrator and tranche handoff

These are concrete handoff requirements; no peer acknowledgment or completed cross-tranche integration is claimed. The studio integrator owns any eventual change to `studio/index.html`.

| Owner | Concrete handoff |
|---|---|
| T01 / studio integrator | Reuse this runner and receipt with the accepted studio/backend revision. Before changing event semantics, obtain the author's intended distinction between Site and social and whether Site-only counts as posted. Then change the single existing implementation and extend its tests; do not create another posting path. Preserve existing exposure records. Do not infer a new publication flag from URL or platform. |
| T04 | Repeat the same invalid URL, two-tap, shortcut, manual-edit, save and reload sequence on the intended physical phone/browser, including keyboard/viewport behavior. Record device, browser, tested revision and result separately. This receipt supplies narrow-width storage/UI proof only. |
| T02 | Keep source/deposit interfaces separate from release logging. Existing `studio-cf/export_db.py` emits per-document `COLLECTION/DOCID.json` from the six known collections and can read local persistence read-only. Preserve record IDs, event types and free-text version labels. `ver: final`, `draft` or `scan` is a label, not a canonical version ID or clearance; the release packet must bind exact source/version/image hashes separately. No broader generator rebuild or deposit/final-version identity is certified here. |
| T06 / T07 | Consume T03's explicit release-clearance contract, exact output/asset inventory and author/filing gates. Neither a logged appearance, a derived number, a false EXPO_PUB value nor this passing local test authorizes publication or automation. |

Read-only coordination sources inspected: T01's existing repository/runtime at `/workspace/scratch/8216ae450607`; T04's `docs/verification/t04-t02-integration-2026-11-05.md` and `site-v4-2026-11-05.md` in `/workspace/scratch/1fc151f82b99/journal-t04`. T04 explicitly records that T02 acknowledgment and physical-device evidence have not been observed. No peer checkout or uncommitted file was edited. The runner uses installed runtime binaries read-only.

The root worker independently compared all four receipt source hashes with the T03 checkout; all matched. The late PR #101 head `e5ae157ef556690e73047e30225cad61c5484cf9` has identical `studio/` and `studio-cf/` blobs, so the application behavior remains the same at that source snapshot. The receipt still names the revision actually tested; it is not relabeled as a new run.

## Source boundaries

Source implementation: `studio/index.html` Mark posted helpers, Calendar and Exposure sections; `studio/cf-adapter.js`; `studio-cf/lib/api.js`; `studio-cf/tests/helpers/{jwt,wrangler}.mjs`, at the tested revision. Relevant historical integration records: PRs [#89](https://github.com/4444J99/journal-handwritten-web/pull/89), [#96](https://github.com/4444J99/journal-handwritten-web/pull/96), [#100](https://github.com/4444J99/journal-handwritten-web/pull/100), and reconciled [#101](https://github.com/4444J99/journal-handwritten-web/pull/101).

The shared packet `2026-10-16-v1.1` / projection `2026-10-16-v1.1-r2`, private project `g-p-6a10bcb4ada4819194e881431212101a`, remains inaccessible. No claim is attributed to unseen contents. Historical approvals are evidence, not new authority.

## Rollback and limits

All servers and the test browser were stopped by the runner's cleanup. The only database state is under the explicitly supplied fresh scratch root. Remove that owned scratch directory to discard the synthetic records; no production rollback is needed. Preserve the JSON receipt and screenshots when handing off. No release record or filing evidence was created in the author's records.

Not exercised: live D1/Access, actual author credentials, physical phone, concurrent clients, repeat-click races before rendering, recovery from a server interruption during a write, complete asset upload/deposit flow, actual release clearance or filing. These limits do not invalidate the demonstrated local write/read/reload behavior.
