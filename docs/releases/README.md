# T03 first-release packet

**Private technical preparation. Not cleared for release.** Start with [the author-decision packet](t03-author-decisions.md), then inspect the actual output and evidence below.

| Deliverable | Location |
|---|---|
| Private visual report and reader preview | [Generated packet](../../release/packets/2026-11-05-t03/index.html) |
| Exact gates, exposure inventory, images, atlas regions, font metadata and output hashes | [packet.json](../../release/packets/2026-11-05-t03/packet.json) |
| Finite author queue | [802 source-linked review records](../../release/packets/2026-11-05-t03/author-review-queue.json) |
| Current first-release queue | [Four candidates in recorded page order](../../release/packets/2026-11-05-t03/first-release-queue.csv) |
| Proposed whitelist change | [Unapplied patch](../../release/packets/2026-11-05-t03/proposed-whitelist.patch) |
| Repeatable procedure and rollback | [Release procedure](t03-release-procedure.md) |
| Sourced policy and issue disposition | [Policy/disposition record](t03-policy-and-disposition.md) |
| Tested revision and check receipts | [Verification record](../verification/t03-release-verification.md) |
| T01/T02/T04/T06/T07 handoff | [Integrator handoff](t03-integrator-handoff.md) and [release-clearance contract](release-clearance-contract.md) |

To inspect the actual reader, run from the repository root:

```sh
python3 -m http.server 8873 --bind 127.0.0.1 \
  --directory release/packets/2026-11-05-t03
```

Open `http://127.0.0.1:8873/`. Serve the packet only on loopback. The comparison deliberately contains withheld material, and the queue contains private source readings. The whole packet must not be deployed. The current `preview/` is a proposed output only; it still lacks author clearance and filing evidence. Its content (text/version data and images) exclusion checks pass, but 13 withheld-page identifiers and PAL/HF block structures remain in `index.html`. Complete technical exclusion is therefore **false**, pending an author metadata rule or a T04/builder fix and a new check. Noindex is retained and is not access control.

`files.json` inventories the generated packet files before that manifest is written, so it excludes itself. The exact proposed public inventory is independently listed under `packet.json.preview.files` and supplies the current exact file count; do not transfer the baseline count or hashes to the refreshed packet.

## Current packet and preserved baseline

The current preparation uses PR #101 head `e5ae157ef556690e73047e30225cad61c5484cf9`. The genuine 38-review/0-release export makes its posting CLI stop at **exit 3** in the empty-release loader. The helper separately uses `studio-cf/import_export.scan` for a private audit and evaluates the existing gates: 38 reviews pass; Series and batch gates are false. No fake release records are inserted.

The original eight-file rehearsal at PR #101 baseline `5d111c13764655312c32ddf1b55390198bc7f70c` / T03 tested-code commit `e0177fa8a53ee41eda31a90253fbab3cc798556e` is retained under [2026-11-05-t03-baseline](../../release/packets/2026-11-05-t03-baseline/index.html). Its exit result, test counts and hashes are historical evidence. The current packet remains at `release/packets/2026-11-05-t03/`; current results belong to its verification receipt. PR #101 review [discussion 4487062599](https://github.com/4444J99/journal-handwritten-web/pull/101#discussion_r4487062599) remains a separate non-dry-run execution gate.
