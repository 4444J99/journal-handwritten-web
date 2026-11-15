-- Series orders for p006-p010 per docs/decisions/2026-11-15-versforms-decide-p006-p010.json (journal PR 163).
-- One D1 batch, mirroring the Studio write path: one vf_revs bump per document, doc rev = current rev.
INSERT INTO vf_revs (collection, rev) VALUES ('release', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;
INSERT INTO vf_docs (collection,id,data,updated_at,rev) VALUES ('release','p006','{"pool":"series","order":5}','2026-11-15T00:00:00.000Z',(SELECT rev FROM vf_revs WHERE collection='release'));
INSERT INTO vf_revs (collection, rev) VALUES ('release', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;
INSERT INTO vf_docs (collection,id,data,updated_at,rev) VALUES ('release','p007','{"pool":"series","order":6}','2026-11-15T00:00:00.000Z',(SELECT rev FROM vf_revs WHERE collection='release'));
INSERT INTO vf_revs (collection, rev) VALUES ('release', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;
INSERT INTO vf_docs (collection,id,data,updated_at,rev) VALUES ('release','p008','{"pool":"series","order":7}','2026-11-15T00:00:00.000Z',(SELECT rev FROM vf_revs WHERE collection='release'));
INSERT INTO vf_revs (collection, rev) VALUES ('release', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;
INSERT INTO vf_docs (collection,id,data,updated_at,rev) VALUES ('release','p009','{"pool":"series","order":8}','2026-11-15T00:00:00.000Z',(SELECT rev FROM vf_revs WHERE collection='release'));
INSERT INTO vf_revs (collection, rev) VALUES ('release', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;
INSERT INTO vf_docs (collection,id,data,updated_at,rev) VALUES ('release','p010','{"pool":"series","order":9}','2026-11-15T00:00:00.000Z',(SELECT rev FROM vf_revs WHERE collection='release'));
