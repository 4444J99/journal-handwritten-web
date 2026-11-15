-- Series orders for p002-p005 per docs/decisions/2026-11-14-versforms-decide.json (journal PR 159).
-- One D1 batch, mirroring the Studio write path: one vf_revs bump per document, doc rev = current rev.
INSERT INTO vf_revs (collection, rev) VALUES ('release', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;
INSERT INTO vf_docs (collection,id,data,updated_at,rev) VALUES ('release','p002','{"pool":"series","order":1}','2026-11-15T00:00:00.000Z',(SELECT rev FROM vf_revs WHERE collection='release'));
INSERT INTO vf_revs (collection, rev) VALUES ('release', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;
INSERT INTO vf_docs (collection,id,data,updated_at,rev) VALUES ('release','p003','{"pool":"series","order":2}','2026-11-15T00:00:00.000Z',(SELECT rev FROM vf_revs WHERE collection='release'));
INSERT INTO vf_revs (collection, rev) VALUES ('release', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;
INSERT INTO vf_docs (collection,id,data,updated_at,rev) VALUES ('release','p004','{"pool":"series","order":3}','2026-11-15T00:00:00.000Z',(SELECT rev FROM vf_revs WHERE collection='release'));
INSERT INTO vf_revs (collection, rev) VALUES ('release', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;
INSERT INTO vf_docs (collection,id,data,updated_at,rev) VALUES ('release','p005','{"pool":"series","order":4}','2026-11-15T00:00:00.000Z',(SELECT rev FROM vf_revs WHERE collection='release'));
