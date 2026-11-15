-- Exact inverse of forward.sql. Release collection held p001-p005 (rev 7) before the change.
DELETE FROM vf_docs WHERE collection='release' AND id IN ('p006','p007','p008','p009','p010');
UPDATE vf_revs SET rev=7 WHERE collection='release';
