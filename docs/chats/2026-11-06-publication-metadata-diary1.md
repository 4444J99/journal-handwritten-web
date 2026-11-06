# Publication metadata and diary1 geometry - 2026-11-06

## Produced

- Confirmed the actual posting path calls `build_public.build`, including the existing exact-membership PAL/HF filter. Single-piece output contains neither withheld page identifiers nor withheld revision structures.
- Public builds blank journal handwriting-font name IDs 0 and 10 on every platform; license fields 13/14, outlines, character map, advances, and timestamp are preserved. Repeated builds are deterministic. The private source font is retained.
- Public builds omit the global machine-transcription review claim. The posting audit reports its omission; the per-line verification gate remains required.
- Inspected the full diary1 scan and repaired block 2: line 1 had pointed to the third ink line, line 2 to the fourth, and line 3 had no region. The canonical source now maps all four lines and rebuilds reader, studio and notes provenance. Original geometry/order is retained for exact archival reconstruction with overlays disabled; raw text, IDs and accepted reviews are unchanged.

## Author decisions

The author rejected deferring the diary1 block 2 repair until after publication and instructed this session to do everything discussed. This authorizes stripping unpublished IDs, blanking optional journal font provenance, removing the public global status line and repairing the mapping. It does not select a release version, classify pieces, supply filing evidence or clear a specific public output.

- Broad verification exposed a Python 3.15 compatibility bug: `datetime.fromisoformat` now accepts 24:00 while the cross-runtime release contract rejects it. Added an explicit hour bound; existing Python/JavaScript contract tests reproduce the failure and pass after the fix. No gate was relaxed.

## Plan / next steps

Run the regression suite, source rebuild/archival checks, public-output inspection and browser checks; record results below. Deliver through a private repository pull request. Public posting continues to use the existing exact-output clearance and release gates.

## Status

Implementation and verification in progress. No public poem upload performed.
