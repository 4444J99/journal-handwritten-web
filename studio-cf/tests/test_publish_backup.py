import sys,json,sqlite3,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import import_export as ie,export_db
class PublishBackup(unittest.TestCase):
 def test_history_exports_and_imports_without_allowing_replacement(self):
  row={'collection':'publish','id':'event.fixture','data':json.dumps({'event':'event.fixture','action':'publish','who':'owner@example.invalid'})}
  docs,rejects=export_db.collect([row]);self.assertEqual(rejects,[])
  conn=sqlite3.connect(':memory:');conn.executescript(ie.build_sql(docs,'first'))
  conn.executescript(ie.build_sql(docs,'second'))
  self.assertEqual(conn.execute("SELECT updated_at FROM vf_docs WHERE collection='publish'").fetchone()[0],'first')
  docs['publish']['event.fixture']['who']='different@example.invalid'
  with self.assertRaises(sqlite3.IntegrityError):conn.executescript(ie.build_sql(docs,'third'))
if __name__=='__main__':unittest.main()
