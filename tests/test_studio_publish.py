"""Offline publication preparation and Python/JS parity; no remote writes."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_public
import test_post_poem as fixtures

SPEC = importlib.util.spec_from_file_location('publish_prepare', ROOT / 'studio-cf' / 'prepare_publish.py')
prep = None
if SPEC and SPEC.loader and Path(SPEC.origin).exists():
    prep = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(prep)

class PreparationTests(unittest.TestCase):
    def test_python_fallback_honors_the_recorded_skip_policy_only(self):
        db={'decisions':{'gruw-policy':{'choice':'skip'}},'batches':{}}
        self.assertTrue(fixtures.post_poem.gate_filed(db,'p001')[0])
        for choice in ('Skip',' skip',None,[],{}):
            db['decisions']['gruw-policy']['choice']=choice
            self.assertFalse(fixtures.post_poem.gate_filed(db,'p001')[0])

    def test_preparation_pins_shell_and_catalogues_only_existing_images(self):
        self.assertIsNotNone(prep, 'offline publisher preparation is implemented')
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); fixtures.make_private(base/'src')
            result=prep.prepare(base/'src', base/'prepared')
            self.assertEqual(len(result['shellSha256']),64)
            self.assertNotIn(build_public.OLD_NAME.lower(), (base/'prepared/shell.html').read_text().lower())
            self.assertEqual(result['metadata'], {'PAL':[], 'HF':[]})
            self.assertEqual(len(result['tiles']), 6)
            for path,asset in result['assets'].items():
                self.assertEqual(asset['sha256'], prep.sha((base/'prepared/assets'/path).read_bytes()))

    def test_data_parity_for_synthetic_release_lists(self):
        self.assertIsNotNone(prep, 'offline publisher preparation is implemented')
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); source=base/'src'; fixtures.make_private(source)
            manifest=prep.prepare(source,base/'prepared')
            for ids in [['p003'], ['p001'], ['p001','p002'], ['p003','p006'],list(fixtures.ORDER)]:
                with self.subTest(pieces=ids):
                    dbpath=base/'db'; fixtures.ready_db(dbpath,pids=fixtures.ORDER,_root=source)
                    db=fixtures.post_poem.load_db(dbpath)
                    payload={'source':manifest,'db':db,'shell':(base/'prepared/shell.html').read_text(),'pieces':ids,'accepted':fixtures.ORDER}
                    runner=ROOT/'studio-cf/tests/compile-fixture.mjs'
                    r=subprocess.run(['node',str(runner)],input=json.dumps(payload),text=True,capture_output=True,check=True)
                    candidate=json.loads(r.stdout)
                    self.assertFalse(candidate['blocked'],candidate['stops'])
                    select={pid:[fixtures.PIECES[pid]['top']] for pid in ids}
                    build_public.build(base/'reference',ids,site=source/'site',select=select,rename_fonts=False)
                    expected=json.loads((base/'reference/data/j.json').read_text())
                    # The planned tiled atlas has one page per texture rather than
                    # one repacked texture. All other data must be exactly equal.
                    expected['atlas']=[manifest['tiles'][p['id']]['size'] for p in expected['pages']]
                    for n,p in enumerate(expected['pages']):p['a']=[n,0,0,*manifest['tiles'][p['id']]['size']]
                    self.assertEqual(candidate['data'],expected)

if __name__ == '__main__': unittest.main()
