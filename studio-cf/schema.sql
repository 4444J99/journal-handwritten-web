-- Review studio storage. Idempotent: safe to apply more than once.
-- Shares a D1 database with another project, so every object here is prefixed vf_
-- and nothing in this file (or anywhere in studio-cf) may touch a non-vf_ object.
--
-- vf_docs: one row per document, addressed like the claude.ai artifact database
--          (collection + id). `data` is the JSON object exactly as the page wrote it.
-- vf_revs: one counter per collection. It is bumped in the same D1 batch (one
--          transaction) as every write, so a client can ask "anything new since N?".
CREATE TABLE IF NOT EXISTS vf_docs (
  collection TEXT NOT NULL,
  id         TEXT NOT NULL,
  data       TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  rev        INTEGER NOT NULL,
  PRIMARY KEY (collection, id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS vf_revs (
  collection TEXT PRIMARY KEY,
  rev        INTEGER NOT NULL
) WITHOUT ROWID;
