# Derived decisions, 2026-11-05

Two documents for the review studio's `decisions` collection, in the same one-file-per-document layout as `exports/studio-db-2026-11-05/`. They are **not** the author's stated choices. The author asked for numbering and participation to be "figured out from logic"; Claude derived them from `docs/plan.md` and labelled them as such in each document's `note`.

| Document | Choice | Reason in one line |
|---|---|---|
| `decisions/release-numbering.json` | `as-posted` | Fixed numbering follows queue position, so a reorder or a move to Reserve would renumber poems already public. |
| `decisions/participation.json` | `around` | The 100 are the author's own poems; group registration needs one claimant per batch; the plan's research points to a separate contributor layer. |

To change either: open the studio's Decisions tab and pick another choice (a second click on the active choice clears it). Import with the studio importer:

```
python3 studio-cf/import_export.py exports/derived-decisions-2026-11-05 --dry-run
```

Technical record only; no poem text.
