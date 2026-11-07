#!/usr/bin/env python3
"""Prepare the pinned engine, immutable image catalogue and per-page atlas tiles.

Runs only on source/engine updates, never on a Studio Publish tap. Output is
private and belongs inside the Access-protected studio deployment. Nothing is
uploaded. The shell contains no private PAL/HF witnesses; they stay in source.json.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_public  # noqa: E402
from variorum_sources import read_supplement
from PIL import Image  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def metadata(html, name):
    match = re.search(r'\bconst\s+' + name + r'\s*=\s*(\[[\s\S]*?\]);', html)
    if not match:
        return [], html
    literal = re.sub(r'([,{]\s*)([A-Za-z_]\w*)\s*:', r'\1"\2":', match.group(1))
    value = json.loads(literal)
    return value, html[:match.start(1)] + '[]' + html[match.end(1):]


def prepare(root, out):
    root, out = Path(root), Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError('preparation output must be new or empty')
    out.mkdir(parents=True, exist_ok=True)
    j = json.loads((root / 'site/data/j.json').read_text())
    review = json.loads((root / 'studio/data/review.json').read_text())
    html = build_public.add_noindex(build_public.remove_public_transcription_status(build_public.rebrand((root / 'site/index.html').read_text())))
    html, reports = build_public.rename_embedded_fonts(html)
    if any(r.get('error') or r.get('hits_after') for r in reports):
        raise ValueError('font did not pass its decoded name check')
    pal, html = metadata(html, 'PAL')
    hf, html = metadata(html, 'HF')
    if build_public.OLD_NAME_RE.search(html):
        raise ValueError('public shell contains a name leak')
    (out / 'shell.html').write_text(html)
    (out / 'blank.html').write_text(build_public.SHELL)
    assets, tiles, hashes = {}, {}, {}

    def add(path, data, content_type):
        path = Path(path).as_posix()
        target = out / 'assets' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        assets[path] = {'sha256': sha(data), 'size': len(data), 'contentType': content_type}

    for sub in ('p', 'i', 'm', 's', 'h'):
        for path in sorted((root / 'site/img' / sub).glob('*.jpg')):
            data = path.read_bytes()
            add(path.relative_to(root / 'site'), data, 'image/jpeg')
            if sub in ('p', 'i', 'm'):
                hashes.setdefault((sub, sha(data)), set()).add(path.stem)
    for name in ('reader-features.js', 'reader-packages.js'):
        path = root / 'site' / name
        if path.is_file():
            text = path.read_bytes()
            if build_public.OLD_NAME_RE.search(text.decode()):
                raise ValueError('reader module contains a name leak')
            add(name, text, 'text/javascript; charset=utf-8')
        elif name in html:
            raise ValueError('missing reader module')
    twins = {}
    for group in hashes.values():
        for pid in group:
            twins.setdefault(pid, set()).update(group - {pid})
    for page in j['pages']:
        if not isinstance(page.get('a'), list) or len(page['a']) != 5:
            continue  # staged sources remain unavailable to the compiler
        n, x, y, w, h = page['a']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', page['id']):
            raise ValueError('invalid page id')
        files = {}
        for kind in ('t', 'k'):
            path = f"tiles/{kind}-{page['id']}.jpg"
            # Lossless PNG bytes under the engine's existing .jpg route retain
            # the exact original crop pixels. R2 serves the real content type.
            # Repacking JPEG would add another lossy encoding per publication.
            import io
            with Image.open(root / 'site/img/a' / f'{kind}{n}.jpg') as original:
                if x < 0 or y < 0 or x + w > original.width or y + h > original.height:
                    raise ValueError('atlas crop outside source image')
                buf = io.BytesIO()
                original.crop((x, y, x + w, y + h)).convert('RGB').save(buf, format='PNG')
                add(path, buf.getvalue(), 'image/png')
            files[kind] = path
        tiles[page['id']] = {'size': [w, h], 'files': files}
    font_records = []
    for match in build_public.DATA_URI_RE.finditer(html):
        import base64
        raw = base64.b64decode(match.group(2))
        if build_public.is_font(match.group(1), raw):
            desc = build_public.run_font_tool('describe', raw)
            font_records.append(desc['name_records'])
    manifest = {'schema': 1, 'j': j, 'review': review, 'variorumSupplement': read_supplement(root),
                'variorumFontEvidence': json.loads((root / 'source/variorum-font-evidence.json').read_text()) if (root / 'source/variorum-font-evidence.json').is_file() else None, 'metadata': {'PAL': pal, 'HF': hf},
                'assets': assets, 'tiles': tiles, 'twins': {k: sorted(v) for k, v in twins.items() if v},
                'shellSha256': sha(html.encode()), 'fonts': reports, 'fontRecords': font_records}
    text = json.dumps(manifest, ensure_ascii=False, separators=(',', ':'))
    (out / 'source.json').write_text(text)
    source_hash = sha(text.encode())
    fragments = {}

    def fragment(path, value):
        value = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value)
        fragments[path] = sha(value.encode())

    page_meta = [{'id': p['id'], 'sp': p.get('sp'), 'B': [{} for _ in p['B']]} for p in j['pages']]
    for piece in j['pieces']:
        needed = {pg for v in piece['V'] for pg, _ in v['P']}
        local_j = dict(j, pages=[p if p['id'] in needed else page_meta[n] for n, p in enumerate(j['pages'])])
        for k in ('acceptedReadings', 'sourceAnchors'):
            if k in j:
                local_j[k] = {lid: value for lid, value in j[k].items()
                              if any(lid in b.get('lineIds', []) or lid.startswith(p['id'] + '-')
                                     for p in j['pages'] if p['id'] in needed for b in p['B'])}
        # Full piece memberships and lightweight page/spread records are needed
        # for shared-scan checks; text and review lines are limited to this piece.
        value = dict(manifest, j=local_j, review=dict(review, pages=[p for p in review['pages'] if p['id'] in needed]))
        fragment(f"pieces/{piece['id']}.json", value)
    for page in j['pages']:
        local_ids = {lid for bi, b in enumerate(page['B']) for lid in
                     b.get('lineIds', [f"{page['id']}-{bi}-{li}" for li in range(len(b['L']))])}
        fragment(f"pages/{page['id']}.json", {'page': page,
                 'acceptedReadings': {lid: tx for lid, tx in j.get('acceptedReadings', {}).items() if lid in local_ids}})
    catalog = {'schema': 1, 'v': j['v'], 'pieces': j['pieces'], 'groups': j['groups'],
               'pageOrder': [p['id'] for p in j['pages']], 'assets': assets, 'tiles': tiles,
               'prov': {k: v for k, v in j['prov'].items() if k in build_public.PROV_KEEP},
               'metadata': manifest['metadata'], 'fontRecords': font_records, 'fragments': fragments,
               'spreadAssets': {p['id']: [f"img/s/{p['sp']['f']}.jpg"] for p in j['pages'] if (p.get('sp') or {}).get('f')},
               'sourceAnchors': {lid: {'status': 'unavailable'} for lid, value in j.get('sourceAnchors', {}).items() if value.get('status') == 'unavailable'},
               'lineIdsByBlock': {f"{p['id']}/{bi}": b.get('lineIds', [f"{p['id']}-{bi}-{li}" for li in range(len(b['L']))])
                                  for p in j['pages'] for bi, b in enumerate(p['B'])}}
    catalog_text = json.dumps(catalog, ensure_ascii=False, separators=(',', ':'))
    (out / 'catalog.json').write_text(catalog_text)
    (out / 'pin.json').write_text(json.dumps({'shellSha256': manifest['shellSha256'],
        'sourceSha256': source_hash, 'catalogSha256': sha(catalog_text.encode())}, indent=2) + '\n')
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    result = prepare(a.root, a.out)
    print(json.dumps({'shellSha256': result['shellSha256'], 'pages': len(result['tiles']), 'assets': len(result['assets'])}))


if __name__ == '__main__':
    main()
