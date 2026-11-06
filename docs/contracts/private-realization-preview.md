# Stored realization packages for private preview

The November 6, 2026 adapter connects an existing immutable Studio realization
revision to the T10 static renderer and the shared private reader lifecycle.
It preserves the realization's history and recorded language, layout and glyph
choices. Exporting or inspecting a package supplies no public clearance.

## Prepare an existing revision

Export the private artifact history from Studio and select the exact existing
realization artifact document. Keep its `revisionDigest`, source binding, parents
and complete `payload.realization` unchanged. The input to this command is that
single artifact document, not the surrounding backup envelope:

```sh
python3 tools/realization_preview_package.py \
  --artifact /path/to/existing-artifact-revision.json \
  --repo /path/to/current/private-checkout \
  --db /path/to/current-studio-export \
  --assets /path/to/existing-glyph-package \
  --out /path/to/new-private-preview
```

The output must be a new directory outside the repository, Studio export and
glyph input. The exporter validates the stored artifact and full realization
history, rechecks the current T02 v2 logical source and actual source policy,
and verifies each declared glyph asset. It rechecks source and policy before
making the completed directory visible. An old source needs an explicit saved
rebind; neither this command nor the viewer creates one.

The printed result identifies the exact artifact revision/digest and a separate
`package` descriptor. Keeping the package descriptor outside the immutable
artifact avoids a circular artifact/package hash. Resolve `manifestUrl` against
the same-origin private directory serving these files.

## Manifest and content

`manifest.json` uses schema `versforms.realization-preview-package.v1`, template
`versforms.t10-static-preview.v1`, a strict file inventory, current source and
policy, outer artifact identity, and inner realization revision/digest.
The descriptor hashes the manifest bytes; the manifest hashes every payload
file and records its byte length and media type. `may_publish` is always false.
Technical fixture history retains its fixture marking.

| File | Purpose |
|---|---|
| `artifact.json` | Exact selected immutable outer artifact revision |
| `realization.json` | Complete validated inner realization history |
| `assets/*` | Original declared, hash-verified font and optional capture manifest |
| `index.html` | Fixed static T10 template with exact selected lines/layout and embedded verified font bytes |

The HTML accepts no caller-supplied markup or arbitrary dependency tree. Its CSP
disables scripts, connections and images; the font is embedded as a data URL.
The consumer verifies the complete inventory, artifact/model identities, font
bytes and fixed template before creating the preview document. Malformed types,
extra dependencies, altered HTML and mismatched stored revisions are refusals.

## Actual Studio and reader inputs

Studio supplies the current selected artifact from its immutable store, current
source from the reviewed catalog, and current policy from the release collection.
The preview JSON cannot replace those trusted providers. For example, its
realization descriptor has this shape, with values copied from the actual export:

```json
{
  "realization": {
    "source": {
      "pieceId": "<existing-piece-id>",
      "versionId": "<existing-version-id>",
      "sourceFingerprint": "sha256:<64-hex-digest>"
    },
    "revisionId": "<selected-stored-artifact-revision>",
    "package": {
      "manifestUrl": "/private-preview/manifest.json",
      "sha256": "sha256:<exact-manifest-bytes-digest>"
    }
  }
}
```

Enable the private controls, choose Realization, then explicitly start it. Source,
policy, selected stored revision and lifecycle state are rechecked across fetches
and before mounting. Raw realization HTML URLs are unsupported.

For the fixed `index.html` entry, the loader requests the package directory URL
directly because Pages canonicalizes an explicit `index.html` request. All
fetches retain `redirect:error`, same-origin validation, exact response-URL
equality, byte limits and hash checks. This is a single known entry mapping,
not permission to follow redirects.

The iframe permits `allow-same-origin` without `allow-scripts`. The parent needs
document access to handle Escape when focus is inside the static preview;
the child cannot execute scripts. Dismissal, source/policy changes, unmounting,
visibility changes and cancellation use the shared lifecycle and remove the
frame. A canceled fetch cannot insert a late preview.

For source-region packages and the distinct current-geometry/media checks, see
[the private region contract](private-region-preview.md). The complete assembled
Studio/API/reader gate is `tools/verify_reader_packages.mjs`; its CLI requires the
actual generated T10/T08 packages, immutable artifact history, region descriptor,
Chromium path and a fresh evidence directory. Run it on loopback with disposable
local D1 state. It does not verify a deployed account or a physical device.
