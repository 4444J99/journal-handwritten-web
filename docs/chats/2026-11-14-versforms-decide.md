# 2026-11-14 versforms decisions p002-p005

## Produced
- `docs/decisions/2026-11-14-versforms-decide.json`: decisions with evidence (issue 105 sort rule, issue 106 GRUW,
  p002 shared scan with x-diary2) and a per-line confidence record for the 70 unreviewed lines of p002-p005
  (plus the Shelley quotation placeholder), compared against the scans.
- `exports/studio-db-delta-2026-11-14/`: read-only export of the live D1 documents that changed since
  `studio-db-2026-11-05` (release p001, decisions, versions); reviews were identical (38 docs, all p001).

## Author decisions
None in this session. The decisions recorded are the orchestrator's, made on the author's delegation, and reversible.

## Plan / next steps (suggestions)
- Apply the p002-p005 Series release docs through the Studio Release tab or `studio-cf/import_export.py`; nothing was written to D1.
- Author confirms or corrects the 12 medium and 1 low confidence lines; none is marked confirmed in D1.

## Status
Data-only PR. No D1 write, no deploy, no filing.
