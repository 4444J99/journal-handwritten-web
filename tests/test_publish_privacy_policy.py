"""Author's 2026-11-06 policy is checked on the actual Python upload tree."""
import base64,json,re,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import build_public,post_poem
import test_post_poem as fixture
class PublicPolicy(unittest.TestCase):
 def test_actual_upload_tree_omits_optional_font_provenance_and_status(self):
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'public'
   result=build_public.build(out,['p001'],site=root/'site',select={'p001':[0]})
   self.assertIsNone(result['font_error'])
   html=(out/'index.html').read_text()
   self.assertFalse('not yet checked' in html, 'public status line is absent')
   self.assertFalse('by the author. Spelling and line breaks kept.' in html, 'public verification claim is absent')
   self.assertNotIn('"diary53a"',html)
   for m in build_public.DATA_URI_RE.finditer(html):
    raw=base64.b64decode(m.group(2))
    if not build_public.is_font(m.group(1),raw):continue
    desc=build_public.run_font_tool('describe',raw)
    self.assertTrue(all(not v for k,v in desc['name_records'].items() if k.split('/')[0] in ('0','10')))
   self.assertFalse(any('not yet checked' in value for _,value in post_poem.audit_strings(out)))
 def test_strip_preserves_license_records_and_font_outlines(self):
  raw=fixture.make_font('Synthetic')
  import subprocess
  py=build_public.font_python()
  script="import sys,io;from fontTools.ttLib import TTFont;f=TTFont(io.BytesIO(sys.stdin.buffer.read()),recalcTimestamp=False);f['name'].setName('Required fixture license',13,3,1,1033);f['name'].setName('https://license.invalid',14,3,1,1033);f.save(sys.stdout.buffer)"
  raw=subprocess.run([py,'-c',script],input=raw,capture_output=True,check=True).stdout
  result=build_public.run_font_tool('rename',raw,'--family','ajp-scribbles','--full','ajp-scribbles Regular','--postscript','ajp-scribbles-Regular','--strip-journal-metadata')
  after=build_public.run_font_tool('describe',base64.b64decode(result['font_b64']))
  before=build_public.run_font_tool('describe',raw)
  for k in ['glyph_order','cmap','hmtx']:self.assertEqual(before[k],after[k])
  self.assertIn('Required fixture license',after['name_records'].values())
  self.assertIn('https://license.invalid',after['name_records'].values())
if __name__=='__main__':unittest.main()
