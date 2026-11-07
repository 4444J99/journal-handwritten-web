# Studio publishing verification - 2026-11-06

Implementation: private code commit 59c83c89cfa29e5c240955db9a0c7a782d507f9e; public reader commit 2e8ecab. Private PR https://github.com/4444J99/journal-handwritten-web/pull/137 and public shell PR https://github.com/4444J99/versforms/pull/2.

## Local checks

| Suite | Result |
| --- | --- |
| Root Python | 391 run, 0 failures, 1 environment skip; 886.629 seconds |
| Root Node | 116 passed |
| Studio Python | 60 passed |
| Studio Node | 132 passed; includes local Pages/D1/R2 integration and fresh scratch build |
| Public reader | 6 passed |
| Integrity | 509 references found, 533 checksums, OK |

The existing skip is test_python_without_fonttools_is_reported: the system interpreter already has fontTools, so that test cannot simulate its absence. No tests or gates were disabled for this implementation. These are local results; GitHub Actions did not execute its check jobs. Its annotation says recent account payments failed or the spending limit must increase.

The review found three Important defects: publication could race a Reserve/review edit, production Unpublish defaulted to staging, and clean-checkout tests relied on a prebuilt ignored dist. All three were reproduced and fixed. A non-expiring D1 revision fence now coordinates source writers and final pointer changes; recovery invalidates delayed R2 conditional writes before releasing the fence. Tests cover confirm, rollback, late completion after recovery and unconfirmed snapshot exclusion. Target selection is preserved and named in confirmation. Integration prepares its own tested assets. The minor client continuation limit was also fixed and tested beyond 1,000 requests.

## Real source parity

A fresh read-only D1 export contained 43 documents: 38 reviews, 4 decisions and 1 release record. p001 passes all three gates without overrides, including the recorded GRUW skip policy. Canonical data SHA-256: 4d6d871caad73c5886b01fa1e8d69cb4c52d3eef035b768aa13d792489b90390. Python and JavaScript match all data except the planned atlas layout, all six non-atlas file hashes, two lossless source-tile pixel comparisons and 22 retained line rectangles. p001 selects V[0]; five corrections are on unpublished versions. No review was changed for this check.

Chrome headless exercised the actual module worker, preview canvas/font, a 390x844 phone viewport, a 960-pixel desktop preview, local-only confirmation, history and unpublish. The fixture uses an isolated local database and buckets; its confirmations do not publish an author's poem. This is browser emulation, not physical iPhone acceptance.

## Hosted state and limits

The staging reader deployment 40249e0f-5da0-4058-bcf1-dedcc732ae18 serves blank paper with noindex and binds only PUBLIC=versforms-staging. Raw public reader access has no D1 or private bucket binding.

The Studio Git build root is studio-cf, output dist, command python3 -m pip install -r requirements-build.txt && python3 build_cloudflare.py. The initial preview failed under the old ../studio output outside the repository; the corrected retry 18f9c423-0c3e-49e4-bf92-2a41aa4962fe deployed successfully. The project root retains functions/ and the authentication middleware, as required by https://developers.cloudflare.com/pages/functions/get-started/. Existing ACCESS_AUD, ACCESS_TEAM_DOMAIN and OWNER_EMAILS secrets, the owner-only Access application for production and wildcard previews, and fail_open=false were preserved. Unauthenticated Studio requests redirect to Access. Hosted owner-session verification remains unconfirmed because the connected browser session closed during sign-in.

The original monolithic synthetic server spike took 24 ms for one page and 166 ms for 123. The implemented free fallback compiles in a browser worker and verifies one piece/page or copies one file per request. Warm synthetic checks were around 3-8 ms; some cold checks reached 11 ms while returning 200. This does not establish universal compliance with a 10-ms CPU limit. No paid plan was activated.

Owner actions remain: review the public shell PR, confirm the first actual p001 snapshot in staging, check a real iPhone and laptop, then confirm production and inspect its release record. The Python posting path remains available. No actual poem was published by this session.

Production Studio deployment 683ee733-18b2-4e99-ab4b-138d5b51e62e is canonical and identifies code commit 59c83c89cfa29e5c240955db9a0c7a782d507f9e. Its production configuration contains DB plus PHOTOS, STAGING and PUBLIC, the browser build mode and exact shell pin; all three existing authentication secrets remain and fail_open=false. Anonymous requests to the page, publication API, private source and review data redirect to Access on both canonical and deployment hostnames. D1 still has no publish history documents. The implementation is deployed from the reviewed feature commit; PRs remain unmerged.

Both new publication buckets have their managed public development domains disabled. The public reader remains the serving boundary.

## Integration follow-up - 2026-11-06

The author said "proceed" after the review/merge/deploy next steps. Two subsequently available automated review findings were independently reproduced before fixing: snapshot base URLs changed bookmark paths, and 60-poem recovery exceeded the free invocation query budget. The actual Chrome history test failed against the old setHash and passes when pathname/query are retained. Recovery now loads release documents once per continuation and processes at most four changes; a 60-poem test enforces 50 D1 calls per request, verifies all 60 numbers/appearances, and verifies fence release. D1 batches count as one invocation query per the current limits documentation: https://developers.cloudflare.com/d1/platform/limits/.

The generated public package additionally checks that staging/production reader and shell copies match and executes permalink handling in both shells. All nine public-package tests pass. The corrected shell pin is 665ce92ac114f06b0f07f18c3ac37d4473a44b1e0507753dd68db85c338d9be1. All author wording, font/license policy and noindex decisions remain intact. The earlier suite counts/deployment IDs above are the pre-integration baseline; the fresh clean-commit full-suite receipt and resulting merged/deployed revisions are reported on the PRs.

### Integration validation outcome

On production-code revision 3fe29af5e6d0cf7cbdf7647ebfde5a4b0832b5ba, integrity, 117 root Node tests, 60 Studio Python tests and 133 Studio Node tests passed. The first full Python attempt ran 391 tests with one skip and one failure inside the test_post_poem.git fixture helper; the summary omitted the caller and the helper supplied no stdout/return-code diagnostics. Five likely Git-fixture cases passed individually. The helper assertion was kept identical and its message now includes command, return code and both output streams. A complete verbose Python rerun then passed all 391 tests with the same one environment skip in 492.894 seconds. The original failure was not reproduced or root-caused; its failed receipt and the full rerun log are retained under ignored .post-poem-work/. No assertion, gate or limit was relaxed.

Public PR #2 merged as 0fff63baeba6192515d640c23f6e7b9a12ee480a. Production reader deployment adafe751-092e-4cbd-ab0f-0535450e5094 and staging deployment 63f4e12f-79d4-47d3-b8a6-39f4314fd75c identify that merged source. Both return blank paper with noindex and refuse data, pointer, source and database routes. Production has only PUBLIC=versforms-public; staging has only PUBLIC=versforms-staging. The private PR's final merge/deployment receipt is maintained in https://github.com/4444J99/journal-handwritten-web/pull/137. GitHub-hosted Actions remains blocked before job execution by account billing/spending; optional review allowance/access limitations were not changed.

### Hosted Access repair and owner sign-in

The owner acceptance check found HTTP 503 after Access returned to the Studio. A bounded live request trace identified studio-auth: key set unavailable: jwks status; the Worker handled requests normally rather than exceeding CPU. The current Access organization certificate endpoint returned 200 with two keys. Only the production ACCESS_TEAM_DOMAIN secret was reset from the account's authoritative Access organization; existing audience/owner secrets, identity providers, JWT validation and owner-only policy were unchanged. The same code revision 952b4f6 was redeployed as 0c8fb998-dd92-4f7f-acd4-ac1e81e2606d. The owner then reported that Studio opens, and the subsequent trace contained page/API requests without signing-key errors. The original secret value is redacted by the API, so its prior literal value was not established. This repairs observed sign-in; first real preview/confirmation and physical-device acceptance remain separate.

### Staging hosting replacement during owner acceptance

The owner confirmed p001 to staging, then reported the live page mixed all poems. D1 recorded only p001 and the R2 snapshot cab9d83ab82dae3cd54f7683a20fecc433e7aa71e9c7b14ac084a4f81883e24f contains only p001, one version and six nonempty text blocks. The live staging host nevertheless returned the full 126-piece source JSON, matching the retained private source. This was an unintended public exposure; third-party access was not established.

The Pages audit records Dashboard actions at 2026-11-07T01:52:03Z connecting versforms-staging to journal-handwritten-web and at 01:52:05Z creating deployment 7d9d71f6-5af8-4400-9878-55738b0d1f2f. That deployment served the private repository's site output with uses_functions=false, bypassing the approved snapshot reader. A subsequent private-repository preview 640d68fe-f28c-4165-ad2a-8b4ac1148e24 had the same problem. The browser audit does not distinguish manual operation from another browser-driven agent.

Containment: staging and its wildcard deployment hostnames were placed behind an owner-only Access application, automatic production and preview Git deployments were disabled, the verified reader was restored and then redeployed as 6dedbec7-2c34-4552-9b0e-821b375081a6 from public commit 0fff63b, and both unintended deployments were deleted. The Git build root was changed to staging/site via root staging and output site, so the private repository's top-level site cannot be selected by that configuration. Original private source and the confirmed p001 snapshot were retained. At this observation, staging remained temporarily owner-only pending final reader verification.

A raw-source site/_worker.js now fails closed on Cloudflare Pages. The regression test deployed a private fixture directory through real local Pages: before the guard the private page returned 200; afterward page, JSON, image and worker routes all returned empty 403/no-store. The approved reader is assembled separately and must not copy this guard. Focused builder tests and all nine public-package tests pass; the complete Studio suite is run with the guard before integration. No reading gate, source filter or auth policy was relaxed.

Guard validation completed: all 134 Studio Node tests pass, all nine public reader/package tests pass, all three publication preparation/parity tests and the private build-preservation test pass, and integrity verification passes with 534 checksums. The real staging release record has one staging appearance dated 2026-11-06, no production number, and no pending source-write fence.
