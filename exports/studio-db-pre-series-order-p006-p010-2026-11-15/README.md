# Pre-change snapshot, Series order write p006-p010 (2026-11-15)

Private repo only. Taken read-only from D1 `studio-documents-prod` (68b1a11f-00a8-4bc7-923b-0931292980c7) before applying Series orders 5-9 to p006-p010 (decision file docs/decisions/2026-11-15-versforms-decide-p006-p010.json, journal PR 163; builds on PR 161).

Table before: vf_docs 60 rows (decisions 4, publish 12, release 5, reviews 38, versions 1); vf_revs 5 rows (decisions 4, publish 12, release 7, reviews 1, versions 1).
Only the `release` collection and the `vf_revs` release counter are touched; the release rows p001-p005 are copied to release/ (they are unchanged by the write). Untouched rows are pinned by checksum, not copied.

Checksums: sha256 over JSON.stringify of rows as arrays [collection,id,data,updated_at,rev] ordered by collection,id (same method as PR 161).
- all vf_docs (60 rows): f178745fc3f14758b8e89604102b24ee49da934a511e0ed24eb31c48b2e51eed
- vf_docs where collection<>'release' (55 rows): 3680c171c5fac75f01263133ca517be84443fd312339d577319801edbfadf72f (identical to the PR 161 value)
- vf_docs where collection='release' (p001-p005, 5 rows): 543b8a5b2dca14a1769b3b9acf45ddfa0ce9e5371956488fd388f6dee17ec0c9
- vf_docs release p001 alone: 57c6e0da7ede4bda872365146ea85d334d056b0a229abc199ea58d8ab8ebf6d7 (identical to PR 161)
- vf_revs where collection<>'release' as [collection,rev]: ea7f63a25a18b20ba9d358ca7afc24d44b9073d59d940318470f33848620e0d7 (identical to PR 161)

Files: forward.sql (the one batch), inverse.sql (exact undo). Outcome: docs/chats/2026-11-15-versforms-d1-write-p006-p010.md.
