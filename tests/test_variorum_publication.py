"""Independent Python/JavaScript composite output parity and hard-stop tests."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import variorum_publication as model
import build_public

SCRIPT = r'''
import {fixture} from './studio-cf/tests/helpers/publish-fixture.mjs';
import {buildVariorumCatalog,provisionalParts,materializeComposite} from './studio/variorum-model.mjs';
import {assembleEffectiveSource,projectPublicVariorum} from './studio/publish-compiler.mjs';
const f=fixture();
const catalog=buildVariorumCatalog({versionMap:f.source.j,review:f.source.review,reviews:f.db.reviews});
const parts=provisionalParts(catalog,'p001');
for(const map of Object.values(parts.maps))for(const os of Object.values(map.segments))for(const o of os)o.accepted=true;
const r=materializeComposite(catalog,parts,[{partId:'part-1',from:'v0',occurrence:1}]);
f.db.parts={'r.map':{...parts,family:'parts',revisionId:'r.map'},'h.p001':{revisionId:'r.map'}};
f.db.composites={'r.comp':{...r,family:'composite',pieceId:'p001',revisionId:'r.comp',partsRevisionId:'r.map',versionId:'c-test'}};
const effective=assembleEffectiveSource(f.source,f.db,{pieces:['p001']});
console.log(JSON.stringify({...f,effective,projection:projectPublicVariorum(effective.j.pieces[0].variorum,[effective.j.pieces[0].V.at(-1)])}));
'''

@unittest.skipUnless(shutil.which('node'), 'Node needed for cross-language vectors')
class PublicationParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = json.loads(subprocess.run(['node', '--input-type=module', '-e', SCRIPT], cwd=ROOT, check=True, capture_output=True, text=True).stdout)

    def test_independent_effective_source_and_filtered_maps_match_js(self):
        actual = model.assemble_effective_source(self.f['source'], self.f['db'], ['p001'])
        self.assertEqual(actual, self.f['effective'])
        pc = actual['j']['pieces'][0]
        self.assertEqual(model.project_public_variorum(pc['variorum'], [pc['V'][-1]]), self.f['projection'])

    def test_python_hard_stops_frozen_text_or_line_tampering(self):
        for field in ('text', 'lines'):
            db = copy.deepcopy(self.f['db'])
            if field == 'text':
                db['composites']['r.comp']['text'] = 'synthetic changed text'
            else:
                db['composites']['r.comp']['lines'][0]['text'] = 'synthetic changed line'
            out = model.assemble_effective_source(self.f['source'], db, ['p001'])
            with self.assertRaisesRegex(ValueError, 'stale_composite_source'):
                model.check_composite(out['j']['pieces'][0]['V'][-1], self.f['source'], db, 'staging')

    def test_glyph_and_pool_gates_are_independent_of_legacy_force(self):
        out = model.assemble_effective_source(self.f['source'], self.f['db'], ['p001'])
        v = out['j']['pieces'][0]['V'][-1]
        with self.assertRaisesRegex(ValueError, 'glyph'):
            model.check_composite(v, self.f['source'], self.f['db'])
        model.check_composite(v, self.f['source'], self.f['db'], 'staging')
        db = copy.deepcopy(self.f['db']); db['release']['p001']['pool'] = 'reserve'
        with self.assertRaisesRegex(ValueError, 'source_pool_withheld'):
            model.check_composite(v, self.f['source'], db, 'staging')

    def test_typeset_only_python_build_preserves_binding_and_removes_provenance(self):
        effective = model.assemble_effective_source(self.f['source'], self.f['db'], ['p001'])
        pc = effective['j']['pieces'][0]
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'public'
            build_public.build(out, ['p001'], site=ROOT / 'site', select={'p001': [len(pc['V'])-1]},
                               source_data=effective['j'], publication_source=self.f['source'],
                               publication_db=self.f['db'], target='staging', rename_fonts=False)
            data = json.loads((out / 'data/j.json').read_text())
            self.assertEqual(data['pages'], [])
            self.assertEqual(data['pieces'][0]['V'][0]['text'], self.f['db']['composites']['r.comp']['text'])
            self.assertIn('p001/c-test', data['sourceBindings'])
            self.assertNotIn('compositeEvidence', json.dumps(data))
            self.assertNotIn('partsRevisionId', json.dumps(data))
            fixture = copy.deepcopy(self.f)
            fixture['db']['decisions']['p001-final'] = {'choice': 'c-test'}
            script = "import {buildCandidate} from './studio/publish-compiler.mjs';let t='';for await(const c of process.stdin)t+=c;const f=JSON.parse(t);const r=await buildCandidate({...f,pieces:['p001'],target:'staging'});if(r.blocked)throw new Error(JSON.stringify(r.stops));console.log(JSON.stringify(r.data));"
            expected = json.loads(subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT,
                                   input=json.dumps(fixture), capture_output=True, text=True, check=True).stdout)
            self.assertEqual(data, expected)


    def test_imported_lyric_photo_promotion_and_linked_repeat_assembly_parity(self):
        script = r"""
import {assembleEffectiveSource} from './studio/publish-compiler.mjs';
import {buildVariorumCatalog,provisionalParts,materializeComposite} from './studio/variorum-model.mjs';
let text='';for await (const c of process.stdin)text+=c;
const f=JSON.parse(text),outputs=[];
for(const kind of ['lyric','notebook','photo','promotion','linked-repeat']){
 const source=structuredClone(f.source),db=structuredClone(f.db);
 if(kind==='lyric'||kind==='notebook'){
  source.variorumSupplement={schemaVersion:1,sources:[{pieceId:'p001',versionId:'imported-'+kind,kind,status:'supplied',lines:[{lineId:'private-import-line',text:'synthetic import',breakBefore:false,verified:true}],exposures:[{type:'download',where:'technical-fixture'}]}]};
 }
 if(kind==='photo'){db.composites['r.comp'].render='photo';db.composites['r.comp'].photo={assetId:'a'.repeat(32),sha256:'b'.repeat(64),size:10,contentType:'image/jpeg'};}
 let pieces=['p001'];
 if(kind==='promotion'){db.composites['r.promote']={family:'promotion',pieceId:'p004',originComposite:{revisionId:'r.comp'}};pieces=['p004'];}
 if(kind==='linked-repeat'){
  const map=db.parts['r.map'];map.linkedPieces=['p002'];
  map.maps.v1={segments:{'part-1':[{occurrence:2,lines:['pg2-0-0'],accepted:true}]},version_part_order:[{partId:'part-1',occurrence:2}]};
  const catalog=buildVariorumCatalog({versionMap:source.j,review:source.review,reviews:db.reviews});
  const r=materializeComposite(catalog,map,[{partId:'part-1',from:'v0',occurrence:1},{partId:'part-1',from:'v1',occurrence:2}]);
  Object.assign(db.composites['r.comp'],r);
 }
 outputs.push({kind,source,db,pieces,expected:assembleEffectiveSource(source,db,{pieces})});
}
console.log(JSON.stringify(outputs));
"""
        variants = json.loads(subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT,
                              input=json.dumps(self.f), text=True, capture_output=True, check=True).stdout)
        for v in variants:
            with self.subTest(kind=v['kind']):
                actual = model.assemble_effective_source(v['source'], v['db'], v['pieces'])
                self.assertEqual(actual, v['expected'])

    def test_photo_bytes_checked_before_existing_output_changes(self):
        db = copy.deepcopy(self.f['db'])
        blob = b'synthetic-technical-photo-fixture'
        photo = {'assetId': 'a' * 32, 'sha256': hashlib.sha256(blob).hexdigest(), 'size': len(blob), 'contentType': 'image/jpeg'}
        db['composites']['r.comp'].update(render='photo', photo=photo)
        effective = model.assemble_effective_source(self.f['source'], db, ['p001'])
        pc = effective['j']['pieces'][0]
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'public'; out.mkdir(); (out / 'sentinel').write_text('preserved')
            options = dict(site=ROOT / 'site', select={'p001': [len(pc['V'])-1]}, source_data=effective['j'],
                           publication_source=self.f['source'], publication_db=db, rename_fonts=False)
            with self.assertRaisesRegex(ValueError, 'photo byte mismatch'):
                build_public.build(out, ['p001'], photo_assets={photo['assetId']: b'wrong'}, **options)
            self.assertEqual((out / 'sentinel').read_text(), 'preserved')
            build_public.build(out, ['p001'], photo_assets={photo['assetId']: blob}, **options)
            self.assertEqual((out / 'img/p/c-test.jpg').read_bytes(), blob)

    def test_sentence_case_preserves_whitespace_and_rejects_bad_mode(self):
        self.assertEqual(model.transform_case('  hELLO!\n\tWoRLD', 'sentence'), '  Hello!\n\tWorld')
        with self.assertRaisesRegex(ValueError, 'invalid_case'):
            model.transform_case('x', 'unknown')

if __name__ == '__main__':
    unittest.main()
