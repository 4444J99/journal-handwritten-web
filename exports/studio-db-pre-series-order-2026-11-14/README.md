# Pre-change snapshot, Series order write (2026-11-14)

Private repo only. Taken read-only from D1 `studio-documents-prod` (68b1a11f-00a8-4bc7-923b-0931292980c7) before applying Series orders 1-4 to p002-p005 (decision file docs/decisions/2026-11-14-versforms-decide.json, journal PR 159).

Table before: vf_docs 56 rows (decisions 4, publish 12, release 1, reviews 38, versions 1); vf_revs 5 rows (decisions 4, publish 12, release 3, reviews 1, versions 1).
Only the `release` collection and the `vf_revs` release counter are touched, so only those are exported (release/p001.json is unchanged by the write). The untouched rows are pinned by checksum, not copied (they hold unpublished journal text already stored in git elsewhere or in D1).

Checksums: sha256 over JSON.stringify of rows as arrays [collection,id,data,updated_at,rev] ordered by collection,id.
- all vf_docs (56 rows): ac2d94c53b06db6ac11252593a9b6b1754fcc80962ae83b77a814d5a626ce300
- vf_docs where collection<>'release' (55 rows): 3680c171c5fac75f01263133ca517be84443fd312339d577319801edbfadf72f
- vf_docs where collection='release' (p001): 57c6e0da7ede4bda872365146ea85d334d056b0a229abc199ea58d8ab8ebf6d7
- vf_revs where collection<>'release' as [collection,rev]: ea7f63a25a18b20ba9d358ca7afc24d44b9073d59d940318470f33848620e0d7

Files: forward.sql (the one batch), inverse.sql (exact undo). Outcome: docs/chats/2026-11-14-versforms-d1-write.md.
