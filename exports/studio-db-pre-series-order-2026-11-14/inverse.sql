-- Exact inverse of forward.sql. Release collection had only p001 (rev 3) before the change.
DELETE FROM vf_docs WHERE collection='release' AND id IN ('p002','p003','p004','p005');
UPDATE vf_revs SET rev=3 WHERE collection='release';
