# T03: first-release technical preparation — November 5, 2026

## Produced

- An isolated T03 branch reusing PR #101's posting gates, review application, final-version selection, public builder, font transformation and noindex checks. The initial `5d111c13764655312c32ddf1b55390198bc7f70c` baseline and tested-code commit `e0177fa8a53ee41eda31a90253fbab3cc798556e` are historical evidence. After the late refresh, the current checkout is based on PR #101 `e5ae157ef556690e73047e30225cad61c5484cf9`. T03 adds no second posting path.
- `tools/prepare_release_packet.py`, its regression tests and `tools/verify_release_preview.cjs`. The current posting CLI stops at **exit 3** on the authentic preserved 38-review/0-release export in its empty-release loader. The helper separately uses `studio-cf/import_export.scan` for a private audit and calls the existing gate functions: 38 reviews pass, Series false, batch false. No fake release records, clearance or source-whitelist writes are introduced.
- A bounded p001 / `p001-diary1-0` private preview. The original eight-file rehearsal remains under `release/packets/2026-11-05-t03-baseline/`; the current packet is generated at `release/packets/2026-11-05-t03-current/`. Its inventory and verification receipt govern current bytes and results.
- Content (text/version data and images) exclusion passes for the bounded preview, but **13 withheld-page identifiers and PAL/HF block structures remain in `index.html`**. Complete technical exclusion is false. The author must rule on that metadata or T04/the builder must remove it and verify the remedy. The private alternative-version comparison deliberately shows diary62a blocks 3 and 4 (p126) and fails image exclusion. The whole review packet must stay private.
- A finite, source-linked 802-record author-review queue in recorded page order; a first-four-candidate queue; an unassigned 100-slot planning tracker; an unapplied whitelist proposal; exact file/image/atlas/font inventory; and rollback instructions.
- Sourced release/Reserve policy and all 13 issue dispositions, an author-decision packet, PR #101 review evidence, a disposable database-backed studio receipt and release-clearance/integrator contracts. The local D1 receipt has 12 passing checks and a narrow desktop 390-pixel viewport, not touch/phone acceptance. The release-browser receipt separately uses touch emulation. No physical-phone pass is claimed.
- Both `docs/plan.md` and restored `claude/plan.md` carry the current addendum. The older `claude-plan-addendum.patch` has already been applied and is retained as a reproducible historical handoff, not a pending patch.

Final independent review corrected a report-count error before delivery: diary62a has 16 reviewed lines (11 confirmed and five corrected), while diary1 has 22 confirmed lines. Issue #113's five corrections agrees with the export. The private report now derives counts from audit data; public preview bytes are unchanged.

## Author decisions

The current instruction authorizes technical preparation in an isolated branch with a draft PR or handoff package. It does not authorize merge, deployment, publication, spending, account changes, external messages, issue closure, repository restructuring, filing or release approval.

No new creative text, editorial classification, first-piece approval, final-version decision, shared-scan exception, withheld-metadata clearance, filing confirmation, Reserve size or first-post date was supplied. Earlier statements are evidence, not fresh authority. p001, as-posted numbering and around-the-100 participation remain derived defaults awaiting confirmation. The recorded title versforms, font family ajp-scribbles, journal-page ordering, weekly cadence and existing-resource/no-spend constraint remain author instructions.

## Plan / next steps

The current proposal replaces elapsed dates with a review step: inspect the exact packet, resolve its decisions and evidence gates, then choose an explicit start date and repeat every seven days. No future date is scheduled or committed.

T01 owns shared studio integration and a fresh complete export; T02 supplies source/deposit interfaces and any image derivative; T04 supplies accepted reader/physical-phone evidence and coordinates a remedy for residual metadata if required. T06/T07 consume only the versioned clearance contract and a specific cleared output manifest. The T04 workspace's stable-ID/sole-reader-source proposal was inspected without modifying that work or claiming integration.

Site and social both have false publication classifications in the UI enum; event payloads do **not** store these as `pub` fields. Mark posted uses type social, while the Site shortcut uses type site. Author semantics must be settled before downstream automation relies on that distinction.

## Status

The source whitelist remains empty. The public CLI's current exit-3 loader refusal and the private audit's separately evaluated gates are distinct results. The 38 line reviews supply neither author release approval nor filing evidence. Residual withheld-page metadata prevents a complete technical-exclusion claim. PR #101 review [4487062599](https://github.com/4444J99/journal-handwritten-web/pull/101#discussion_r4487062599), concerning multiple push URLs, remains a non-dry-run execution gate.

The private shared packet `2026-10-16-v1.1`, projection `2026-10-16-v1.1-r2`, in project `g-p-6a10bcb4ada4819194e881431212101a` remained inaccessible. No conclusion is attributed to unseen contents.

Live observations and source limits are recorded in `docs/releases/t03-source-register.json`; exact test outcomes and final commit identities belong to the integrator's verification receipt. Historical baseline counts are not current acceptance. Other workers' checkouts and uncommitted work were preserved. No release-readiness claim is made.
