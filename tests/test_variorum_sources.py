import importlib.util,json,tempfile,unittest
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('variorum_sources',Path(__file__).resolve().parents[1]/'tools/variorum_sources.py');m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
class SourceTests(unittest.TestCase):
 def test_missing_inputs_fail(self):
  with tempfile.TemporaryDirectory()as d:
   with self.assertRaisesRegex(ValueError,'required'):m.read_supplement(d)
 def test_import_corrections_preserve_original_bytes_and_lines(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);(root/'source/external').mkdir(parents=True);(root/'source/canonical.json').write_text(json.dumps({'pieces':[{'id':'p001'}]}));f=root/'source/external/author.txt';f.write_bytes(b'alpha\r\n\r\nbeta\r\n')
   proposal=m.import_text(root,'p001','lyric',f);self.assertFalse((root/'source/variorum.json').exists());self.assertTrue(proposal['changed'])
   first=m.import_text(root,'p001','lyric',f,True);old=m.read_supplement(root)['sources'][0];self.assertEqual((root/old['file']).read_bytes(),b'alpha\r\n\r\nbeta\r\n');self.assertFalse(any(l['verified']for l in old['lines']))
   f.write_text('gamma\n');second=m.import_text(root,'p001','lyric',f,True);self.assertNotEqual(first['versionId'],second['versionId']);saved=m.read_supplement(root);self.assertEqual(len(saved['sources']),2);self.assertEqual(saved['sources'][0]['lines'],old['lines']);self.assertFalse(m.import_text(root,'p001','lyric',f)['changed'])
