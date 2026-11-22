# Provenance — `versforms` Notebook Externalization (2026-11-22)

* **Source:** `versforms` research notebook
* **Export Date:** `2026-11-22`
* **Destination Repository:** `4444J99/journal-handwritten-web` (private source of record)
* **Base Commit (`main`):** `b2b92b7c2a41e046c27ebf25b326e9d8937d0ebe`
* **Integrity Check:** All files live exclusively under `docs/chats/`. Neither `site/`, `studio/`, `release/public.json`, nor `MANIFEST.sha256` was modified.

## Branch-to-File Ledger

| Branch | Path | Completeness | Notes |
| :--- | :--- | :--- | :--- |
| `docs/notebook-export-index-20261122` | `docs/chats/2026-11-22-versforms-notebook-externalization.md` + `.../PROVENANCE.md` | `complete` | Master index, locked decisions, cross-repo agent handoff |
| `docs/notebook-chat-01-variorum-coordinates` | `docs/chats/2026-11-22-versforms-notebook-externalization/01-variorum-coordinates-and-schema.md` | `partial-excerpt` | Retrieved sections preserved verbatim; clipped segments explicitly marked |
| `docs/notebook-chat-02-post-metadata-ast-tei` | `docs/chats/2026-11-22-versforms-notebook-externalization/02-post-metadata-captures-and-tei.md` | `partial-excerpt` | Retrieved sections preserved verbatim; full Python script bodies clipped in retrieval |
| `docs/notebook-chat-03-generative-audio-scores` | `docs/chats/2026-11-22-versforms-notebook-externalization/03-generative-audio-from-variorum-metadata.md` | `verbatim-retrieved` | Complete retrieved prompt & response |
| `docs/notebook-chat-04-repo-ecosystem-map` | `docs/chats/2026-11-22-versforms-notebook-externalization/04-cross-repo-ecosystem-map.md` | `verbatim-retrieved` | Both retrieved turns mapping 9 core + 16 adjacent repos |
| `docs/notebook-chat-05-archival-civilization-witnesses` | `docs/chats/2026-11-22-versforms-notebook-externalization/05-archival-civilization-and-witness-pipeline.md` | `verbatim-complete` | Full verbatim transcript of the `2026-11-22` session |

## Upgrading Partial Excerpts to Full Verbatim Transcripts

Chats 01 and 02 were exported from notebook retrieval excerpts because no direct bulk-export API for historical notebook threads was available during the session. To upgrade either file to `verbatim-complete`:

1. Check out the corresponding branch (`docs/notebook-chat-01-variorum-coordinates` or `docs/notebook-chat-02-post-metadata-ast-tei`) or open a follow-up commit on `main` after merging.
2. Replace the `[... retrieved excerpt boundary ...]` blocks with the full copy/pasted turns from the notebook.
3. Update `completeness: "verbatim-complete"` in the file's YAML frontmatter and in this ledger.
