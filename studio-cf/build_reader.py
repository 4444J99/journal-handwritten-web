#!/usr/bin/env python3
"""Build the reviewable, blank public-reader package; never include private data.

The output is suitable for the versforms public repository after review. Staging
has its own configuration directory so Pages cannot bind its reader to production.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(out, prepared):
    out, prepared = Path(out), Path(prepared)
    if out.exists() and any(out.iterdir()):
        raise ValueError('reader output must be new or empty')
    pin = json.loads((prepared / 'pin.json').read_text())
    shell = (prepared / 'shell.html').read_bytes()
    if hashlib.sha256(shell).hexdigest() != pin['shellSha256']:
        raise ValueError('public shell pin mismatch')
    config = '''name = "versforms"
compatibility_date = "2026-11-06"
pages_build_output_dir = "site"

[[r2_buckets]]
binding = "PUBLIC"
bucket_name = "versforms-public"

[env.preview]
[[env.preview.r2_buckets]]
binding = "PUBLIC"
bucket_name = "versforms-staging"
'''
    staging = '''name = "versforms-staging"
compatibility_date = "2026-11-06"
pages_build_output_dir = "site"

[[r2_buckets]]
binding = "PUBLIC"
bucket_name = "versforms-staging"
'''
    files = {
        'site/index.html': (prepared / 'blank.html').read_bytes(),
        'site/shell.html': shell,
        'site/_headers': b'/*\n  X-Robots-Tag: noindex\n',
        'site/_routes.json': b'{"version":1,"include":["/*"],"exclude":[]}',
        'lib/public-reader.js': (ROOT / 'studio-cf/lib/public-reader.js').read_bytes(),
        'functions/[[path]].js': b"import {readPublic} from '../lib/public-reader.js';\nexport function onRequest({request,env}) {return readPublic(request,env);}\n",
        'staging/functions/[[path]].js': b"import {readPublic} from '../lib/public-reader.js';\nexport function onRequest({request,env}) {return readPublic(request,env);}\n",
        'staging/lib/public-reader.js': (ROOT / 'studio-cf/lib/public-reader.js').read_bytes(),
        'staging/package.json': b'{"name":"versforms-staging-reader","private":true,"type":"module"}\n',
        'wrangler.toml': config.encode(),
        'staging/wrangler.toml': staging.encode(),
        'shell.json': (json.dumps({'shellSha256': pin['shellSha256']}, indent=2) + '\n').encode(),
        'package.json': b'{"name":"versforms-reader","private":true,"type":"module","scripts":{"test":"node --test tests/*.test.mjs"}}\n',
        'tests/public-reader.test.mjs': (ROOT / 'studio-cf/tests/public-reader.unit.test.mjs').read_bytes(),
    }
    # Keep staging's build output inside its own project directory. Pages dev
    # resolves configuration from that output; ../site selects the parent
    # production reader's bucket even when --cwd names the staging directory.
    for name, data in list(files.items()):
        if name.startswith('site/'):
            files['staging/' + name] = data
    for name, data in files.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return {'shellSha256': pin['shellSha256'], 'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--prepared', type=Path, default=ROOT / 'studio-cf/dist/publish')
    args = ap.parse_args()
    result = build(args.out, args.prepared)
    print(json.dumps(result))
