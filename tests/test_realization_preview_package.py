"""The actual T10 model/font package, immutable storage identity and refusals."""
import base64
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import realization_preview_package as package
import script_realizations as sr
from test_script_realizations import envelope, latest, reseal, source
from make_test_font import build


def stored(value):
    document = copy.deepcopy(value["realizations"][0])
    last = document["revisions"][-1]
    artifact = {"schemaVersion": 1, "family": "artifact", "kind": "realization",
                "recordId": "technical-package", "revisionId": "technical-package-r1", "parents": [],
                "source": {"pieceId": document["pieceId"], "versionId": document["versionId"], "sourceFingerprint": last["source"]["versionFingerprint"]},
                "payload": {"realization": document}, "fixture": True, "at": "2026-11-06T18:30:00.123Z",
                "by": "synthetic package test", "reason": "initial"}
    artifact["revisionDigest"] = sr.digest(artifact)
    return artifact


def current_existing_fixture():
    original = sr.read_json(ROOT / "docs/verification/t10-2026-11-05/pilot/realization.json")
    value = copy.deepcopy(original)
    doc = value["realizations"][0]
    prior = doc["revisions"][-1]
    current = sr.source_snapshot(ROOT, doc["pieceId"], doc["versionId"], ROOT / "exports/studio-db-2026-11-05")
    if current["versionFingerprint"] != prior["source"]["versionFingerprint"]:
        # Deliberate fixture rebind; retain the original v1 model as history.
        revision = copy.deepcopy(prior)
        revision.update(id="technical-package-source-rebind", parent=prior["digest"],
                        at="2026-11-06T18:30:00Z", actor="technical integration test",
                        change="source-rebind", source=current)
        doc["revisions"].append(sr.seal(revision))
    sr.validate(value)
    return original, value


def mixed_fixture_history():
    """Synthetic flag-composition case; supplied text/font and history stay intact."""
    original, value = current_existing_fixture()
    prior = stored(value)
    prior.update(recordId="technical-mixed-package", revisionId="technical-mixed-package-r1")
    prior["revisionDigest"] = sr.digest({k: v for k, v in prior.items() if k != "revisionDigest"})
    document = value["realizations"][0]
    old = document["revisions"][-1]
    revision = copy.deepcopy(old)
    revision.update(id="technical-mixed-model-revision", parent=old["digest"],
                    at="2026-11-06T18:31:00Z", actor="synthetic fixture-composition test",
                    change="realization-edit", fixture=False,
                    method={"kind": "human-supplied", "normalization": "preserve",
                            "evidence": "Synthetic contract case, not an author submission; supplied text and font are unchanged."})
    revision["authors"].append({"id": "synthetic-mixed-realizer", "role": "realizer",
                                "evidence": "Synthetic test role only; no author decision or new creative content."})
    document["revisions"].append(sr.seal(revision))
    sr.validate(value)
    current = stored(value)
    current.update(recordId=prior["recordId"], revisionId="technical-mixed-package-r2",
                   parents=[prior["revisionId"]], at="2026-11-06T18:31:00.123Z", reason="revision")
    current["revisionDigest"] = sr.digest({k: v for k, v in current.items() if k != "revisionDigest"})
    return original, value, [prior, current]


def reader_boundary(output, mutation="none"):
    """Run the production loader over actual exported bytes, stopping at DOM parse."""
    script = r"""
import fs from 'node:fs';
import path from 'node:path';
import {createHash,webcrypto} from 'node:crypto';
const folder=process.argv[1],mutation=process.argv[2];
const M=await import('data:text/javascript;base64,'+fs.readFileSync('site/reader-packages.js').toString('base64'));
const hash=bytes=>'sha256:'+createHash('sha256').update(bytes).digest('hex');
const encode=value=>Buffer.from(JSON.stringify(value));
const manifest=JSON.parse(fs.readFileSync(path.join(folder,'manifest.json')));
const stored=JSON.parse(fs.readFileSync(path.join(folder,'artifact.json')));
const files=new Map(manifest.files.map(entry=>[entry.path,fs.readFileSync(path.join(folder,entry.path))]));
if(mutation==='manifest-cleared')manifest.fixture=false;
if(mutation==='manifest-array')manifest.fixture=[true];
if(mutation==='artifact-array'||mutation==='history-cleared'||mutation==='revision-array'){
  if(mutation==='artifact-array')stored.fixture=[true];
  if(mutation==='history-cleared'){stored.fixture=false;manifest.fixture=false;}
  if(mutation==='revision-array'){
    const revision=stored.payload.realization.revisions.at(-1);revision.fixture=[false];
    const {digest,...body}=revision;revision.digest=hash(M.packageJSON(body));manifest.realization.revisionDigest=revision.digest;
    files.set('realization.json',encode({format:'versforms-script-realizations',schemaVersion:1,realizations:[stored.payload.realization]}));
  }
  const {revisionDigest,...body}=stored;stored.revisionDigest=hash(M.packageJSON(body));
  manifest.artifactDigest=stored.revisionDigest;files.set('artifact.json',encode(stored));
}
for(const entry of manifest.files){const bytes=files.get(entry.path);entry.bytes=bytes.length;entry.sha256=hash(bytes);}
const manifestBytes=encode(manifest);let parseCalls=0,requests=0,error;
const doc={baseURI:'http://127.0.0.1:8123/',defaultView:{crypto:webcrypto,btoa,
  fetch:async(url,options)=>{if(options.redirect!=='error'||options.credentials!=='same-origin')throw new Error('Transport guard changed');requests++;const name=new URL(url).pathname.replace(/^\/package\//,'')||'index.html';const bytes=name==='manifest.json'?manifestBytes:files.get(name);if(!bytes)throw new Error('Undeclared request');const response=new Response(bytes);Object.defineProperty(response,'url',{value:url});return response;},
  DOMParser:class{parseFromString(){parseCalls++;throw new Error('VALID_TEMPLATE_REACHED_DOM_BOUNDARY');}}
}};
try{await M.loadRealizationPackage({doc,descriptor:{revisionId:stored.revisionId,package:{manifestUrl:'/package/manifest.json',sha256:hash(manifestBytes)}},source:stored.source,scope:{current:()=>true,signal:new AbortController().signal},getCurrentSource:()=>stored.source,getCurrentPolicy:()=>manifest.policy,getStoredArtifact:()=>stored});}catch(e){error=e.message;}
process.stdout.write(JSON.stringify({parseCalls,requests,error}));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script, str(output), mutation],
                            cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class RealizationPreviewPackage(unittest.TestCase):
    def test_exported_mixed_fixture_history_reaches_reader_without_relabeling_revision(self):
        original, value, history = mixed_fixture_history()
        artifact = history[-1]
        self.assertTrue(artifact["fixture"])
        self.assertFalse(latest(value)["fixture"])
        self.assertEqual(value["realizations"][0]["revisions"][:-1], history[0]["payload"]["realization"]["revisions"])
        self.assertEqual(latest(value)["lines"], latest(original)["lines"])
        self.assertEqual(latest(value)["glyphAssets"], latest(original)["glyphAssets"])
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "mixed-package"
            package.export_package(artifact, ROOT, ROOT / "exports/studio-db-2026-11-05",
                                   ROOT / "docs/verification/t10-2026-11-05/pilot", output)
            manifest = sr.read_json(output / "manifest.json")
            self.assertTrue(manifest["fixture"])
            self.assertFalse(manifest["may_publish"])
            self.assertEqual(sr.read_json(output / "artifact.json"), artifact)
            self.assertEqual(sr.read_json(output / "realization.json"), value)
            markup = (output / "index.html").read_text()
            self.assertIn("Private author-supplied realization — not cleared for release", markup)
            self.assertNotIn("<h1>Technical fixture", markup)
            result = reader_boundary(output)
            self.assertEqual(result, {"parseCalls": 1, "requests": 5,
                                      "error": "VALID_TEMPLATE_REACHED_DOM_BOUNDARY"})
            for mutation in ("manifest-cleared", "manifest-array", "artifact-array", "revision-array", "history-cleared"):
                with self.subTest(mutation=mutation):
                    result = reader_boundary(output, mutation)
                    self.assertEqual(result["parseCalls"], 0, result)
                    self.assertRegex(result["error"], "Unsupported|stored realization|fixture history")

    def test_existing_fixture_font_full_history_and_studio_digest_survive_package(self):
        original, value = current_existing_fixture()
        artifact = stored(value)
        baseline = {path: (ROOT / path).read_bytes() for path in ("site/data/j.json", "studio/data/review.json", "release/public.json")}
        assets = ROOT / "docs/verification/t10-2026-11-05/pilot"
        font = latest(value)["glyphAssets"][0]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "package"
            result = package.export_package(artifact, ROOT, ROOT / "exports/studio-db-2026-11-05", assets, output)
            manifest = sr.read_json(output / "manifest.json")
            self.assertEqual(result["package"]["sha256"], sr.file_hash(output / "manifest.json"))
            self.assertEqual(manifest["artifactDigest"], artifact["revisionDigest"])
            self.assertEqual(manifest["source"], artifact["source"])
            self.assertEqual(manifest["policy"], {"pool": "unsorted", "visibility": "private"})
            self.assertTrue(manifest["fixture"])
            self.assertFalse(manifest["may_publish"])
            self.assertEqual({row["path"] for row in manifest["files"]}, {"index.html", "realization.json", "artifact.json", font["path"]})
            for row in manifest["files"]:
                self.assertEqual(row["sha256"], sr.file_hash(output / row["path"]))
                self.assertEqual(row["bytes"], (output / row["path"]).stat().st_size)
            self.assertEqual(sr.read_json(output / "realization.json"), value)
            self.assertEqual(sr.read_json(output / "artifact.json"), artifact)
            self.assertEqual(value["realizations"][0]["revisions"][0], original["realizations"][0]["revisions"][0])
            self.assertEqual(latest(value)["lines"], latest(original)["lines"])
            markup = (output / "index.html").read_text()
            encoded_font = re.search(r"url\('data:font/otf;base64,([^']+)'\)", markup).group(1)
            self.assertEqual(base64.b64decode(encoded_font, validate=True), (assets / font["path"]).read_bytes())
            self.assertEqual((output / font["path"]).read_bytes(), (assets / font["path"]).read_bytes())
            self.assertIn('data-template="versforms.t10-static-preview.v1"', markup)
            self.assertIn("script-src 'none'", markup)
            self.assertIn("font-src data:", markup)
            self.assertNotIn("font-src 'self'", markup)
            self.assertNotIn("<script", markup)
            self.assertIn("Technical fixture", markup)
            checked = subprocess.run(["node", "--input-type=module", "-e",
                "import fs from 'node:fs';import {assertArtifact} from './studio/artifact-model.mjs';const doc=JSON.parse(fs.readFileSync(0,'utf8'));assertArtifact('artifacts',doc);process.stdout.write(doc.revisionDigest);"],
                cwd=ROOT, input=json.dumps(artifact, ensure_ascii=False), text=True, capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(checked.stdout, artifact["revisionDigest"])
        for path, data in baseline.items():
            self.assertEqual((ROOT / path).read_bytes(), data)

    def inputs(self, parent, text="A B C"):
        root = parent / "inputs"
        (root / "assets").mkdir(parents=True)
        font = root / "assets/test.otf"
        font.write_bytes(build("Synthetic package fixture", "none"))
        value = envelope(text)
        latest(value)["glyphAssets"][0]["sha256"] = sr.file_hash(font)
        reseal(value)
        db = parent / "db"
        db.mkdir()
        return stored(value), value, root, db

    def export(self, artifact, value, assets, db, output, *, current=None, policy=None):
        with patch.object(sr, "source_snapshot", return_value=current or latest(value)["source"]), patch.object(sr, "release_policy", return_value=policy or {"pool": "unsorted", "visibility": "private"}):
            return package.export_package(artifact, ROOT, db, assets, output)

    def test_exact_package_is_deterministic_and_cannot_overwrite_existing_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            artifact, value, assets, db = self.inputs(parent)
            (assets / "assets/unlisted.js").write_text("throw new Error('must not be copied')")
            first, second = parent / "first", parent / "second"
            self.export(artifact, value, assets, db, first)
            self.export(artifact, value, assets, db, second)
            a = {p.relative_to(first): p.read_bytes() for p in first.rglob("*") if p.is_file()}
            b = {p.relative_to(second): p.read_bytes() for p in second.rglob("*") if p.is_file()}
            self.assertEqual(a, b)
            self.assertNotIn(Path("assets/unlisted.js"), a)
            with self.assertRaisesRegex(sr.Invalid, "new independent"):
                self.export(artifact, value, assets, db, first)
            self.assertEqual(a, {p.relative_to(first): p.read_bytes() for p in first.rglob("*") if p.is_file()})

    def test_stale_source_and_nonprivate_eligible_policy_refused_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            artifact, value, assets, db = self.inputs(parent)
            output = parent / "package"
            with self.assertRaisesRegex(sr.Invalid, "stale"):
                self.export(artifact, value, assets, db, output, current=source("A C"))
            for policy in ({"pool": "reserve", "visibility": "private"}, {"pool": "archive", "visibility": "private"}, {"pool": "unsorted", "visibility": "withheld"}, {"pool": "unknown", "visibility": "private"}):
                with self.subTest(policy=policy), self.assertRaisesRegex(sr.Invalid, "excluded"):
                    self.export(artifact, value, assets, db, output, policy=policy)
                self.assertFalse(output.exists())

    def test_original_v1_fixture_is_readable_but_requires_explicit_rebind_to_export(self):
        original, _ = current_existing_fixture()
        sr.validate(original)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "package"
            with self.assertRaisesRegex(sr.Invalid, "stale"):
                package.export_package(stored(original), ROOT, ROOT / "exports/studio-db-2026-11-05",
                                       ROOT / "docs/verification/t10-2026-11-05/pilot", output)
            self.assertFalse(output.exists())

    def test_tampered_font_or_linked_assets_refused_without_partial_package(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            artifact, value, assets, db = self.inputs(parent)
            font = assets / "assets/test.otf"
            font.write_bytes(font.read_bytes() + b"changed")
            with self.assertRaisesRegex(sr.Invalid, "changed"):
                self.export(artifact, value, assets, db, parent / "package")
            self.assertFalse((parent / "package").exists())
            font.unlink()
            font.symlink_to(ROOT / "tests/make_test_font.py")
            with self.assertRaisesRegex(sr.Invalid, "linked"):
                self.export(artifact, value, assets, db, parent / "package")
            self.assertFalse((parent / "package").exists())

    def test_source_and_policy_are_rechecked_before_directory_becomes_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            artifact, value, assets, db = self.inputs(parent)
            output = parent / "package"
            with patch.object(sr, "source_snapshot", return_value=latest(value)["source"]), patch.object(sr, "release_policy", side_effect=[{"pool": "unsorted", "visibility": "private"}, {"pool": "reserve", "visibility": "private"}]):
                with self.assertRaisesRegex(sr.Invalid, "changed during"):
                    package.export_package(artifact, ROOT, db, assets, output)
            self.assertFalse(output.exists())
            self.assertEqual(list(parent.glob(".t10-preview-package-*")), [])

    def test_stored_digest_identity_and_fixture_history_are_not_caller_assertions(self):
        value = envelope()
        for mutate, error in [(lambda a: a.update(revisionDigest="sha256:" + "f" * 64), "digest"),
                              (lambda a: a["payload"].update(unknown=True), "payload"),
                              (lambda a: a.update(fixture=False), "fixture history"),
                              (lambda a: a["source"].update(versionId="other"), "sources differ"),
                              (lambda a: a.update(revisionId=["coerced"]), "identity")]:
            artifact = stored(value)
            mutate(artifact)
            with self.subTest(error=error), self.assertRaisesRegex(sr.Invalid, error):
                package.validate_artifact(artifact)

    def test_combining_run_stanza_language_and_direction_survive_static_export(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            artifact, value, assets, db = self.inputs(parent, "A\u0301 C <script>technical</script>")
            last = latest(value)
            last["source"]["lines"][0]["breakBefore"] = True
            last["source"]["versionFingerprint"] = sr.source_fingerprint(last["source"])
            last["lines"][0]["breakBefore"] = True
            last["language"] = "und"
            last["layout"] = {"direction": "rtl", "writingMode": "vertical-rl"}
            reseal(value)
            artifact = stored(value)
            output = parent / "package"
            self.export(artifact, value, assets, db, output)
            self.assertEqual(sr.read_json(output / "realization.json"), value)
            markup = (output / "index.html").read_text()
            self.assertIn('class="line stanza fallback"', markup)
            self.assertIn('lang="und" dir="rtl"', markup)
            self.assertIn('writing-mode:vertical-rl', markup)
            self.assertIn('A\u0301 C &lt;script&gt;technical&lt;/script&gt;', markup)
            self.assertNotIn('<script>', markup)
            self.assertNotIn('Á C', markup)


if __name__ == "__main__":
    unittest.main()
