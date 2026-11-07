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
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_public  # noqa: E402
import post_poem  # noqa: E402
from PIL import Image  # noqa: E402


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def verify(root, prepared, db_path, pieces, all_versions=(), accepted=()):
    root, prepared = Path(root), Path(prepared)
    src = post_poem.Source(root)
    db = post_poem.load_db_with_root(db_path, set(src.pieces))[1]
    source = json.loads((prepared / 'source.json').read_text())
    payload = {'source': source, 'db': db, 'shell': (prepared / 'shell.html').read_text(),
               'pieces': pieces, 'allVersions': list(all_versions), 'accepted': list(accepted), 'force': True}
    run = subprocess.run(['node', str(ROOT / 'studio-cf/tests/compile-fixture.mjs')],
                         input=json.dumps(payload), text=True, capture_output=True, check=True)
    candidate = json.loads(run.stdout)
    if candidate['blocked']:
        raise ValueError('candidate has hard stops: ' + json.dumps(candidate['stops']))
    select = {pid: post_poem.select_versions(src, db, pid, pid in all_versions)[0] for pid in pieces}
    corrections = {}
    for pid in pieces:
        values, _, stale = post_poem.load_corrections(src, db, pid, select[pid])
        if stale:
            raise ValueError('stale review IDs: ' + ','.join(stale))
        corrections.update(values)
    with tempfile.TemporaryDirectory(prefix='parity-', dir=root / '.post-poem-work') as scratch:
        out = Path(scratch) / 'python'
        build_public.build(out, pieces, site=root / 'site', select=select, corrections=corrections)
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
    args = ap.parse_args()
    print(json.dumps(verify(args.root, args.prepared, args.db, args.piece, args.all_versions, args.accept_shared_scan), indent=2))
