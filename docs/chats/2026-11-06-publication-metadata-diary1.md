# Publication metadata and diary1 geometry - 2026-11-06

## Produced

- Confirmed the actual posting path calls `build_public.build`, including the existing exact-membership PAL/HF filter. Single-piece output contains neither withheld page identifiers nor withheld revision structures.
- Public builds blank journal handwriting-font name IDs 0 and 10 on every platform; license fields 13/14, outlines, character map, advances, and timestamp are preserved. Repeated builds are deterministic. The private source font is retained.
- Public builds omit the global machine-transcription review claim. The posting audit reports its omission; the per-line verification gate remains required.
- Inspected the full diary1 scan and repaired block 2: line 1 had pointed to the third ink line, line 2 to the fourth, and line 3 had no region. The canonical source now maps all four lines and rebuilds reader, studio and notes provenance. Original geometry/order is retained for exact archival reconstruction with overlays disabled; raw text, IDs and accepted reviews are unchanged.

- Broad verification exposed a Python 3.15 compatibility bug: `datetime.fromisoformat` now accepts 24:00 while the cross-runtime release contract rejects it. Added an explicit hour bound; existing Python/JavaScript contract tests reproduce the failure and pass after the fix. No gate was relaxed.

## Author decisions

The author rejected deferring the diary1 block 2 repair until after publication and instructed this session to do everything discussed. This authorizes stripping unpublished IDs, blanking optional journal font provenance, removing the public global status line and repairing the mapping. It does not select a release version, classify pieces, supply filing evidence or clear a specific public output.

## Plan / next steps

Private PR #136 carries the fixes and verification. Public posting continues to use the existing exact-output clearance and release gates.

## Status

All four requested items are implemented and verified. Python: 386 tests run, no failures, one skip (439.162 seconds). JavaScript: 116 pass. Canonical reconstruction: 12 pass; source regions: 58 pass; metadata: 11 pass. Reference/checksum gate: 509 references, zero missing, 528 checksums. Independent review found a license-field rewrite case, repaired with a seeded regression; final review found no additional issues.

Private and generated-public reader matrices pass desktop/mobile light/dark. Public runtime confirms all four block-2 lines have active scan links in every cell. Final release packet passes content and metadata exclusion and is byte-identical to the browser-tested HTML. Its actual gated dry run still exits 3 on the existing empty-release decision state; no classification, filing, exact-output clearance or public poem upload is claimed.

### External checks

GitHub Actions run 42309912506 did not start because account payments/spending admission failed (existing owner #111). Cloudflare preview c2c366bb-489d-469a-847a-acd6799cc4f0 cloned this commit but failed before deployment: the project has an empty root/build command and `../studio` output, outside the repository. Hosting configuration and Access acceptance remain separately owned (#104/#113); no billing or hosting settings were changed. See [the verification receipt](../integration/publication-metadata-diary1-verification-2026-11-06.json).
