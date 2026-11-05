-- Review studio storage. Idempotent: safe to apply more than once.
--
-- docs: one row per document, addressed like the claude.ai artifact database
--       (collection + id). `data` is the JSON object exactly as the page wrote it.
-- revs: one counter per collection. It is bumped in the same D1 batch (one
--       transaction) as every write, so a client can ask "anything new since N?".
CREATE TABLE IF NOT EXISTS docs (
  collection TEXT NOT NULL,
  id         TEXT NOT NULL,
  data       TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  rev        INTEGER NOT NULL,
  PRIMARY KEY (collection, id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS revs (
  collection TEXT PRIMARY KEY,
  rev        INTEGER NOT NULL
) WITHOUT ROWID;
