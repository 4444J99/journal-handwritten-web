# T02 private source acceptance — 2026-11-06

Base integration commit: `104be9cb000800bfc5c01b8a9ebbbbdf5e218922`.

## Observed results

| Check | Result |
| --- | --- |
| Source identity | 123 pages, 126 pieces, 156 versions, 2,190 existing line IDs retained. |
| Raw reconstruction | Both original JSON byte hashes reconstructed exactly without overlays. |
| Available reviews | 38 applied: 33 confirmed and five corrected; all raw originals retained. |
| Second review application | Zero changed records; no new backup or history event. |
| Second rebuild | Zero changed output files. |
| Source image inventory | 505 existing image assets match their captured hashes. |
| Current HTML | Reader and studio HTML match the base commit byte for byte. |
| Independent recovery | Full source/state restored outside the checkout; the restored CLI reports zero rebuild changes. |
| Source/T10/glyph tests | 41 passed. |
| JS source/notes/store/backup tests | 35 passed. |
| Repository integrity | 509 references, zero missing; 519 checksums, pass with the intended content manifest regenerated. |

`source-preservation.json` records template and original-source hashes, current
source counts, the accepted p001 version fingerprint and separate geometry
fingerprint. `review-dry-run.json`, `review-application.json` and
`review-second-application.json` retain the complete per-review change reports.
`rebuild.json` and `rebuild-repeat.json` identify exact changed and unchanged
data bytes. Backup/restore receipts identify the independent destinations and
verified manifest digest; `restored-rebuild.json` records the independent no-op.

The preserved real export currently contains only its `reviews` collection.
The synthetic recovery suite separately exercises every current collection
(`reviews`, `decisions`, `versions`, `release`, `batches`, `rconfig`, `notes`,
`contributions`, `artifacts`) and a future collection. Forked histories and all
original bytes survive; no live or unrelated database is modified.

Additional correction and photo-ingest tests use disposable technical fixtures.
The new version has explicit stable IDs, links to its existing synthetic piece,
preserved JPEG bytes and deterministic display derivatives. Its original text
is null, its compatible text is empty and marked untranscribed, its source boxes
and atlas cell are absent, and its clearance is null. None of those synthetic
records enters the author's canonical inventory.

The direct vector checks cover Python/source/T10 and JavaScript/T05. The shared
`source_binding` API is supplied for T08/T09 integration by the shared-file
owner. Geometry-only movement and pixel changes invalidate geometry/media
bindings while leaving the logical text digest unchanged; a stanza-only change
invalidates v2. Legacy v1 note history remains readable and requires explicit
rebind before current output.

## Reproduction

```sh
python3 -m unittest tests.test_source_foundation tests.test_script_realizations tests.test_glyph_workflow -v
node --test tests/test_source_fingerprint.mjs tests/test_notes_model.mjs tests/test_notes_backup.mjs tests/test_notes_store.mjs
python3 tools/notes_sources.py --check
python3 tools/source_foundation.py validate
python3 tools/source_foundation.py rebuild
```

The source lane does not commit the shared `MANIFEST.sha256`; the integration
owner regenerates it once all lanes are combined. `integrity.log` records the
passing check against this lane's intended content. No external filing,
publication, public repository change or author clearance was performed.
