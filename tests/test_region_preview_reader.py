#!/usr/bin/env python3
"""Actual T08 exporter/reader policy parity; all clearance metadata is synthetic."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import source_regions as regions
from test_source_regions import cleared_policy, reseal

PILOT = ROOT / "docs/pilots/t08-p001/p001.source-regions.json"
POLICY = ROOT / "docs/pilots/t08-p001/visibility-policy.json"
ATOM = "vf:atom:p001/p001-diary1-0/diary1/line-0-0"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def reader_image_boundary(output, descriptor, mutation=None):
    """Use exported bytes and independent current source; stop at image decoding.

    Node has no browser image decoder. The decoder sentinel is reached only
    after the production loader has verified the package, current source,
    policy, geometry and independently read current media bytes.
    """
    script = r"""
import fs from 'node:fs';
import path from 'node:path';
import {createHash,webcrypto} from 'node:crypto';
const folder=process.argv[1],descriptor=JSON.parse(process.argv[2]),mutation=JSON.parse(process.argv[3]);
const M=await import('data:text/javascript;base64,'+fs.readFileSync('site/reader-packages.js').toString('base64'));
const hash=bytes=>'sha256:'+createHash('sha256').update(bytes).digest('hex');
const encode=value=>Buffer.from(JSON.stringify(value));
const manifest=JSON.parse(fs.readFileSync(path.join(folder,'region-preview.json')));
const files=new Map(manifest.files.map(entry=>[entry.path,fs.readFileSync(path.join(folder,entry.path))]));
if(mutation){
  const value=mutation.file?JSON.parse(files.get(mutation.file)):manifest;
  let parent=value;for(const key of mutation.keys.slice(0,-1))parent=parent[key];
  if(mutation.remove)delete parent[mutation.keys.at(-1)];else parent[mutation.keys.at(-1)]=mutation.value;
  if(mutation.file)files.set(mutation.file,encode(value));
}
for(const entry of manifest.files){const bytes=files.get(entry.path);entry.bytes=bytes.length;entry.sha256=hash(bytes);}
for(const [file,key] of [['region-manifest.json','manifestDigest'],['geometry.json','geometryDigest'],['policy.json','policyDigest'],['assets/source.jpg','mediaDigest']]){
  manifest[key]=hash(files.get(file));descriptor[key]=manifest[key];
}
const manifestBytes=encode(manifest);descriptor.package={manifestUrl:'/package/region-preview.json',sha256:hash(manifestBytes)};
const reader=JSON.parse(fs.readFileSync('site/data/j.json'));
const source=reader.sourceBindings['p001/p001-diary1-0'];
const review=JSON.parse(fs.readFileSync('studio/data/review.json'));
const page=review.pages.find(p=>p.id==='diary1');
const geometry={pageId:page.id,width:page.w,height:page.h,blocks:page.blocks.map((b,index)=>({index,lines:b.lines.map(l=>({lineId:l.id,box:l.box??null,sourceAnchor:l.sourceAnchor??null}))}))};
const currentMedia=fs.readFileSync('site/img/p/diary1.jpg');
let imageDecodeCalls=0,currentMediaReads=0,requests=0,error;
const doc={baseURI:'http://127.0.0.1:8123/',defaultView:{crypto:webcrypto,
  fetch:async(url,options)=>{
    if(options.redirect!=='error'||options.credentials!=='same-origin')throw new Error('Transport guard changed');
    requests++;const pathname=new URL(url).pathname;let bytes;
    if(pathname==='/current-source.jpg'){currentMediaReads++;bytes=currentMedia;}
    else if(pathname==='/package/region-preview.json')bytes=manifestBytes;
    else if(pathname.startsWith('/package/'))bytes=files.get(pathname.slice('/package/'.length));
    if(!bytes)throw new Error('Undeclared request');
    const response=new Response(bytes);Object.defineProperty(response,'url',{value:url});return response;
  },
  createImageBitmap:async()=>{imageDecodeCalls++;throw new Error('VERIFIED_REGION_REACHED_IMAGE_DECODER');}
}};
try{await M.loadRegionPackage({doc,descriptor,source,
  scope:{current:()=>true,signal:new AbortController().signal},
  getCurrentSource:()=>source,getCurrentPolicy:()=>({pool:'unsorted',visibility:'private'}),
  getCurrentReviewGeometry:()=>geometry,getCurrentRegionMedia:()=>'/current-source.jpg'});
}catch(e){error=e.message;}
process.stdout.write(JSON.stringify({imageDecodeCalls,currentMediaReads,requests,error}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script, str(output),
         json.dumps(descriptor), json.dumps(mutation)],
        cwd=ROOT, text=True, capture_output=True, check=True,
    )
    return json.loads(result.stdout)


class RegionPreviewReaderPolicy(unittest.TestCase):
    def setUp(self):
        self.manifest = load(PILOT)
        self.policy = cleared_policy(self.manifest)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def export(self, policy=None, name="package"):
        output = self.folder / name
        descriptor = regions.export_private_preview(
            self.manifest, self.policy if policy is None else policy,
            ATOM, output, repo=ROOT,
        )
        return output, descriptor

    def assert_private_image(self, output, descriptor):
        result = reader_image_boundary(output, descriptor)
        self.assertEqual(result["imageDecodeCalls"], 1, result)
        self.assertEqual(result["currentMediaReads"], 1, result)
        self.assertEqual(result["error"], "VERIFIED_REGION_REACHED_IMAGE_DECODER")
        package = load(output / "region-preview.json")
        self.assertIs(package["mayPublish"], False)
        self.assertEqual(package["scope"], "private-local")
        self.assertIs(load(output / "policy.json")["publication"]["enabled"], False)

    def test_cleared_release_gate_does_not_revoke_private_inspection(self):
        original = copy.deepcopy(self.policy)
        self.assertIs(self.policy["release_gate"]["may_publish"], True)
        output, descriptor = self.export()
        self.assert_private_image(output, descriptor)
        self.assertEqual(load(output / "policy.json"), original)
        self.assertEqual(self.policy, original)

    def test_separate_external_gate_flags_do_not_grant_private_publication(self):
        for publish, schedule in ((False, False), (False, True), (True, False), (True, True)):
            with self.subTest(publish=publish, schedule=schedule):
                policy = copy.deepcopy(self.policy)
                policy["release_gate"].update(may_publish=publish, may_schedule_external_actions=schedule)
                output, descriptor = self.export(policy, f"flags-{publish}-{schedule}")
                self.assert_private_image(output, descriptor)
                self.assertEqual(load(output / "policy.json"), policy)

    def test_private_inspection_does_not_require_a_cleared_or_present_release_gate(self):
        derived = load(POLICY)
        absent = copy.deepcopy(derived)
        absent.pop("release_gate")
        for name, policy in (("uncleared", derived), ("absent", absent)):
            with self.subTest(name=name):
                output, descriptor = self.export(policy, name)
                self.assert_private_image(output, descriptor)

    def test_private_publication_flag_remains_strictly_false(self):
        output, descriptor = self.export()
        for value in (True, None, 0, "false", [False]):
            with self.subTest(value=value):
                policy = copy.deepcopy(self.policy)
                policy["publication"]["enabled"] = value
                with self.assertRaises(ValueError):
                    self.export(policy, "invalid-publication")
                self.assertFalse((self.folder / "invalid-publication").exists())
                result = reader_image_boundary(output, descriptor, {
                    "file": "policy.json", "keys": ["publication", "enabled"], "value": value,
                })
                self.assertEqual(result["imageDecodeCalls"], 0, result)
                self.assertIn("private, nonpublishing", result["error"])
        result = reader_image_boundary(output, descriptor, {
            "file": "policy.json", "keys": ["publication", "enabled"], "remove": True,
        })
        self.assertEqual(result["imageDecodeCalls"], 0, result)
        self.assertIn("private, nonpublishing", result["error"])

    def test_package_scope_and_publication_remain_private_after_integrity_reseal(self):
        output, descriptor = self.export()
        mutations = [
            {"keys": ["mayPublish"], "value": value} for value in (True, None, 0, "false", [False])
        ] + [{"keys": ["scope"], "value": value} for value in ("public-release", None, ["private-local"])]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = reader_image_boundary(output, descriptor, mutation)
                self.assertEqual(result["imageDecodeCalls"], 0, result)
                self.assertIn("private scope", result["error"])

    def test_private_manifest_scope_remains_required_with_cleared_release_gate(self):
        output, descriptor = self.export()
        for field, value in (("distribution", "public-release"), ("may_publish", True), ("may_publish", 0)):
            with self.subTest(field=field, value=value):
                manifest = copy.deepcopy(self.manifest)
                manifest["scope"][field] = value
                with self.assertRaises(ValueError):
                    regions.export_private_preview(reseal(manifest), self.policy, ATOM,
                                                   self.folder / "invalid-scope", repo=ROOT)
                self.assertFalse((self.folder / "invalid-scope").exists())
                result = reader_image_boundary(output, descriptor, {
                    "file": "region-manifest.json", "keys": ["scope", field], "value": value,
                })
                self.assertEqual(result["imageDecodeCalls"], 0, result)
                self.assertIn("private, nonpublishing", result["error"])

    def test_private_withholding_and_vetoes_still_refuse_a_cleared_gate(self):
        output, descriptor = self.export()
        cases = [
            (["withheld_pages"], ["diary1"]),
            (["withheld_assets"], [self.manifest["source_assets"][0]["asset_id"]]),
            (["pieces", "p001", "withheld_versions"], ["p001-diary1-0"]),
            (["pieces", "p001", "piece_vetoes"], [{"scopes": ["private-local"]}]),
        ]
        for keys, value in cases:
            with self.subTest(keys=keys):
                policy = copy.deepcopy(self.policy)
                parent = policy
                for key in keys[:-1]:
                    parent = parent[key]
                parent[keys[-1]] = value
                with self.assertRaises(ValueError):
                    self.export(policy, "vetoed")
                self.assertFalse((self.folder / "vetoed").exists())
                result = reader_image_boundary(output, descriptor, {"file": "policy.json", "keys": keys, "value": value})
                self.assertEqual(result["imageDecodeCalls"], 0, result)
                self.assertRegex(result["error"], "withholds|veto")


if __name__ == "__main__":
    unittest.main()
