import json, sqlite3, sys, unittest
import argparse, os, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import import_export as ie
class RestoreHeads(unittest.TestCase):
 def setup_db(self):
  db=sqlite3.connect(':memory:');db.executescript((ie.HERE/'schema.sql').read_text());db.execute('INSERT INTO vf_revs VALUES(?,?)',('parts',7))
  for k,v in [('r.old',{'revisionId':'r.old','text':'old'}),('h.p001',{'recordId':'p001','revisionId':'r.old'})]:db.execute('INSERT INTO vf_docs VALUES(?,?,?,?,?)',('parts',k,json.dumps(v),'before',7))
  db.commit();return db
 def docs(self):return {'parts':{'r.new':{'schemaVersion':1,'family':'parts','recordId':'p001','revisionId':'r.new','text':'new'},'h.p001':{'schemaVersion':1,'recordId':'p001','revisionId':'r.new'}}}
 def test_explicit_cas_preserves_history_and_advances_feed(self):
  db=self.setup_db();db.executescript(ie.build_sql(self.docs(),'now',reconcile_heads={'parts/h.p001':'r.old'}));self.assertEqual(json.loads(db.execute("SELECT data FROM vf_docs WHERE id='h.p001'").fetchone()[0])['revisionId'],'r.new');self.assertEqual(db.execute("SELECT count(*) FROM vf_docs WHERE collection='parts'").fetchone()[0],3);self.assertEqual(db.execute("SELECT rev FROM vf_revs WHERE collection='parts'").fetchone()[0],8)
 def test_wrong_head_rejects_before_any_history_or_feed_write(self):
  db=self.setup_db()
  with self.assertRaises(sqlite3.IntegrityError):db.executescript(ie.build_sql(self.docs(),'now',reconcile_heads={'parts/h.p001':'r.stale'}))
  self.assertEqual(db.execute("SELECT count(*) FROM vf_docs WHERE collection='parts'").fetchone()[0],2);self.assertEqual(db.execute("SELECT rev FROM vf_revs WHERE collection='parts'").fetchone()[0],7)
 def test_publication_fence_blocks_reconciliation(self):
  db=self.setup_db();db.execute('INSERT INTO vf_docs VALUES(?,?,?,?,?)',('publish','source-write-fence','{}','before',0));db.commit()
  with self.assertRaises(sqlite3.IntegrityError):db.executescript(ie.build_sql(self.docs(),'now',reconcile_heads={'parts/h.p001':'r.old'}))
  self.assertEqual(db.execute("SELECT count(*) FROM vf_docs WHERE collection='parts'").fetchone()[0],2)

 def test_reconciliation_rejects_self_head_or_wrong_record(self):
  for change in ['self','wrong-record','wrong-family']:
   docs=self.docs()
   if change=='self':docs['parts']['h.p001']['revisionId']='h.p001'
   elif change=='wrong-record':docs['parts']['r.new']['recordId']='other'
   else:docs['parts']['r.new']['family']='composite'
   with self.assertRaisesRegex(ValueError,'imported immutable revision'):ie.build_sql(docs,'now',reconcile_heads={'parts/h.p001':'r.old'})
 def test_null_expected_means_absent_even_for_malformed_existing_head(self):
  db=self.setup_db();db.execute("UPDATE vf_docs SET data='{}' WHERE id='h.p001'");db.commit()
  with self.assertRaises(sqlite3.IntegrityError):db.executescript(ie.build_sql(self.docs(),'now',reconcile_heads={'parts/h.p001':None}))
  self.assertEqual(db.execute("SELECT rev FROM vf_revs WHERE collection='parts'").fetchone()[0],7)
  self.assertIsNone(db.execute("SELECT id FROM vf_docs WHERE id='r.new'").fetchone())
 def test_empty_non_object_reconciliation_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'must be an object'):ie.build_sql(self.docs(),'now',reconcile_heads=[])

 @unittest.skipUnless(os.environ.get('WRANGLER_BIN'), 'local D1 runtime not configured')
 def test_local_d1_file_failure_rolls_back_earlier_writes(self):
  with tempfile.TemporaryDirectory(prefix='restore-atomic-') as tmp:
   root=Path(tmp);path=root/'late-failure.sql'
   path.write_text((ie.HERE/'schema.sql').read_text()+"\nINSERT INTO vf_revs VALUES('parts',99);\nINSERT INTO vf_docs VALUES('parts','deliberate-failure',NULL,'',0);\n")
   args=argparse.Namespace(wrangler=os.environ['WRANGLER_BIN'],timeout=30)
   with self.assertRaises(SystemExit):ie.run_local(args,path,root/'state')
   files=list((root/'state').rglob('*.sqlite'));self.assertTrue(files)
   for file in files:
    conn=sqlite3.connect(file)
    try:self.assertEqual(conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vf_revs'").fetchall(),[])
    finally:conn.close()

 def test_legacy_source_restore_also_respects_publication_fence(self):
  db=self.setup_db();db.execute('INSERT INTO vf_docs VALUES(?,?,?,?,?)',('publish','source-write-fence','{}','before',0));db.commit()
  with self.assertRaises(sqlite3.IntegrityError):db.executescript(ie.build_sql({'release':{'p001':{'pool':'series'}}},'now'))
  self.assertIsNone(db.execute("SELECT id FROM vf_docs WHERE collection='release'").fetchone())
  self.assertIsNone(db.execute("SELECT rev FROM vf_revs WHERE collection='release'").fetchone())
