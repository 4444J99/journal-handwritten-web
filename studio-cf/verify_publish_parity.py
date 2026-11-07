#!/usr/bin/env python3
"""Compare a private Studio candidate with the real Python posting build.

No upload, git mutation or release-list write. Poem text is never printed. The
only data normalization is the explicitly planned per-page atlas layout. Every
other JSON value and every non-atlas upload file must match. Lossless tile pixels
are checked against the decoded source crop, including every line rectangle.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_public  # noqa: E402
import post_poem  # noqa: E402
import variorum_publication  # noqa: E402
from PIL import Image  # noqa: E402


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def verify(root, prepared, db_path, pieces, all_versions=(), accepted=(), target="production", photo_root=None):
    root, prepared = Path(root), Path(prepared)
    src = post_poem.Source(root)
    db_root, db = post_poem.load_db_with_root(db_path)
    for collection in ('parts', 'composites'):
        db[collection] = {}
        if (db_root / collection).is_symlink():
            raise ValueError('symlink supplemental collection')
        for path in sorted((db_root / collection).glob('*.json')):
            if path.is_symlink() or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', path.stem) or path.stem in ('.', '..'):
                raise ValueError('symlink supplemental export')
            value = json.loads(path.read_text(), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite supplemental input')))
            if not isinstance(value, dict):
                raise ValueError('invalid supplemental export document')
            db[collection][path.stem] = value
    source = json.loads((prepared / 'source.json').read_text())
    payload = {'source': source, 'db': db, 'shell': (prepared / 'shell.html').read_text(),
               'pieces': pieces, 'allVersions': list(all_versions), 'accepted': list(accepted), 'force': True, 'target': target}
    run = subprocess.run(['node', str(ROOT / 'studio-cf/tests/compile-fixture.mjs')],
                         input=json.dumps(payload), text=True, capture_output=True, check=True)
    candidate = json.loads(run.stdout)
    if candidate['blocked']:
        raise ValueError('candidate has hard stops: ' + json.dumps(candidate['stops']))
    effective = variorum_publication.assemble_effective_source(source, db, pieces)
    inventory = {p['id']: p for p in effective['j']['pieces']}
    select, corrections = {}, {}
    for pid in pieces:
        pc = inventory[pid]
        finals = {i for i, v in enumerate(pc['V']) for key, decision in db['decisions'].items()
                  if key.endswith('-final') and decision.get('choice') != 'layers' and
                  (decision.get('choice') == v['id'] or any(decision.get('choice') == f'{pg}-{bi}' for pg, bs in v['P'] for bi in bs))}
        if len(finals) > 1:
            raise ValueError('conflicting_final_decisions')
        select[pid] = list(range(len(pc['V']))) if pid in all_versions else sorted(finals) if finals else [pc['top']]
        for vi in select[pid]:
            for pg, blocks in pc['V'][vi]['P']:
                page = next(p for p in source['j']['pages'] if p['id'] == pg)
                for bi in blocks:
                    for li, text in enumerate(page['B'][bi]['L']):
                        lid = f'{pg}-{bi}-{li}'
                        review = db['reviews'].get(lid)
                        if review and review.get('original') != text:
                            raise ValueError('stale source transcript')
                        if review and review.get('status') == 'corrected':
                            corrections[(pg, bi, li)] = review['text']
    photo_assets = {}
    for pid, indices in select.items():
        for vi in indices:
            v = inventory[pid]['V'][vi]
            if v.get('render') == 'photo':
                asset = v['compositeEvidence']['photo']['assetId']
                if photo_root is None:
                    raise ValueError('photo parity requires --photo-root with original exported asset bytes')
                photo_assets[asset] = Path(photo_root) / asset
    (root / '.post-poem-work').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='parity-', dir=root / '.post-poem-work') as scratch:
        out = Path(scratch) / 'python'
        build_public.build(out, pieces, site=root / 'site', select=select, corrections=corrections, source_data=effective['j'], publication_source=source, publication_db=db, target=target, photo_assets=photo_assets)
        expected = json.loads((out / 'data/j.json').read_text())
        expected['atlas'] = [source['tiles'][p['id']]['size'] for p in expected['pages']]
        for n, page in enumerate(expected['pages']):
            page['a'] = [n, 0, 0, *source['tiles'][page['id']]['size']]
        # Canonicalize BOTH values in the same numeric model. Python preserves
        # 1.0 in JSON while JavaScript writes 1; these are the same JSON number.
        # Comparing Python's textual float spelling would report false drift.
        compare = subprocess.run(['node', '--input-type=module', '-e', '''
import {pathToFileURL} from 'node:url';
const {canonical,digest}=await import(pathToFileURL(process.argv[1]));
let input='';for await(const c of process.stdin)input+=c;
const {expected,actual}=JSON.parse(input),a=canonical(expected),b=canonical(actual);
console.log(JSON.stringify({equal:a===b,sha256:await digest(a)}));
''', str(ROOT / 'studio-cf/lib/publish.js')],
            input=json.dumps({'expected': expected, 'actual': candidate['data']}),
            text=True, capture_output=True, check=True)
        compared = json.loads(compare.stdout)
        if not compared['equal']:
            raise ValueError('Python/JavaScript data mismatch (text withheld from diagnostic)')
        checked = []
        for file in candidate['files']:
            if file['path'].startswith('img/a/') or file['path'] == 'data/j.json':
                continue
            path = out / file['path']
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != file['sha256']:
                raise ValueError('upload file mismatch: ' + file['path'])
            checked.append(file['path'])
        original_pages = {p['id']: p for p in src.j['pages']}
        pixel_checks, line_boxes = 0, 0
        for page in candidate['data']['pages']:
            original = original_pages[page['id']]
            n, x, y, w, h = original['a']
            for kind in ('t', 'k'):
                with Image.open(root / 'site/img/a' / f'{kind}{n}.jpg') as atlas:
                    pixels = atlas.crop((x, y, x + w, y + h)).convert('RGB')
                    tile_file = source['tiles'][page['id']]['files'][kind]
                    with Image.open(prepared / 'assets' / tile_file) as tile:
                        if pixels.size != tile.size or pixels.tobytes() != tile.convert('RGB').tobytes():
                            raise ValueError('atlas tile pixel mismatch: ' + page['id'])
                pixel_checks += 1
            # Data parity has already compared every retained line rectangle.
            line_boxes += len(page.get('x', []))
    return {'pieces': pieces, 'canonicalDataSha256': compared['sha256'],
            'dataParity': True, 'nonAtlasFilesChecked': checked,
            'losslessSourceTilePixelChecks': pixel_checks, 'publishedLineRectangles': line_boxes,
            'atlasNormalization': 'one lossless source-page tile per texture; all other data exact',
            'gates': candidate['gates'], 'versions': candidate['versions']}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--prepared', type=Path, default=ROOT / 'studio-cf/dist/publish')
    ap.add_argument('--db', type=Path, required=True)
    ap.add_argument('--piece', action='append', required=True)
    ap.add_argument('--all-versions', action='append', default=[])
    ap.add_argument('--accept-shared-scan', action='append', default=[])
    ap.add_argument('--target', choices=('production', 'staging'), default='production')
    ap.add_argument('--photo-root', type=Path)
    args = ap.parse_args()
    print(json.dumps(verify(args.root, args.prepared, args.db, args.piece, args.all_versions, args.accept_shared_scan, args.target, args.photo_root), indent=2))
