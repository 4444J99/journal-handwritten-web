# Variorum and Builder: reconciliation and draft review

Inspected 7 November 2026 against source commit `c5e119425be30a4a734a511b33c561a294136437` and reader commit `8bd13aad1d03d81c5401d94d692d0d3f0f683c28`. No live resources changed.

## Deployment inventory

| URL | HTTP observation | Cloudflare configuration |
| --- | --- | --- |
| https://versforms-studio.pages.dev/ | Access sign-in | journal-handwritten-web/main, root studio-cf, output dist |
| https://playground.versforms-studio.pages.dev/ | Access sign-in | Studio preview alias; exact deployment commit not yet inspected |
| https://versforms.pages.dev/ | 200, title versforms | versforms/main, root repository, output site |
| https://versforms-staging.pages.dev/ | 200, title versforms | journal-handwritten-web/main, root staging, output site |

Studio builds with `python3 -m pip install -r requirements-build.txt && python3 build_cloudflare.py`. Its canonical deployment is `71db6e96-fc71-4fd6-8d2a-7ad88bfde9b6`, source commit as above. Reader deployment is `4584b311-091f-4799-a06a-4af3ca1348bf`, reader commit as above. Staging deployment is `6dedbec7-2c34-4552-9b0e-821b375081a6`, commit `0fff63baeba6192515d640c23f6e7b9a12ee480a`.

The Studio Access application covers the root and `*.versforms-studio.pages.dev` with an owner-only allow policy. Existing middleware also verifies JWT signature, issuer, audience, expiry and membership. Sign-in redirects do not establish authenticated UI behavior.

Studio binds DB to object-lessons-submissions (`f1a89504-2ddd-4c9b-ade8-eb52f6aee7a3`). Read-only sqlite_master inspection found vf_docs and vf_revs, plus unrelated submissions and Cloudflare _cf_KV. Neither vf_parts nor vf_composites exists. Preserve unrelated tables.

Studio binds PHOTOS=versforms-studio-assets, STAGING=versforms-staging and PUBLIC=versforms-public in both preview and production. Preview is not a storage sandbox. Reader production has only PUBLIC=versforms-public; reader previews and staging use versforms-staging.

**Deployment discrepancy:** staging's configured source is journal-handwritten-web/root staging, but that directory is absent from the inspected checkout. The standalone staging package exists in versforms. Inspect deployment history before changing source configuration.

## Phase 0.5

Legacy archive/, review_build/ and app_build/ directories are absent. Current source is source/canonical.json; tools/source_foundation.py implements reconstruction/review/rebuild/restore. tools/build_public.py and studio-cf/prepare_publish.py prepare filtered, pinned publication inputs. studio-cf/build_dist.py assembles Studio and private playground. studio-cf/lib/publish*.js handles fenced publication into immutable R2 snapshots. Do not create a parallel archive just to run the drafts.

The repository plan records that artifact v4 was copied into site/index.html on 5 November. Original builder recovery remains unresolved; canonical reconstruction does not establish parity with inaccessible artifacts. Engine changes must update the reviewed reader package and matching Studio shell pin. Infrastructure is verified; complete Phase 0.5 parity is not claimed.

## Five-file review

### functions_api_variorum.js

- `assertCloudflareAccess` accepts arbitrary assertion/email headers or ALLOW_LOCAL_DEV. Reuse existing verified context.data.user identity and owner write authorization. The live middleware/policy reduces exposure; this is a defect in the draft handler, not proof of a deployed bypass.
- Both save branches pre-read revision, condition the upsert, ignore meta.changes and return success. A racing write can change zero rows and still return 200. Initial insert conflicts can overwrite another revision-one insert. Require atomic conditional writes and check affected rows.
- Independent table writes bypass current publication source capture/fencing. Materialized text, verification and exposure are accepted from the client rather than resolved from authoritative source. Include new inputs in capture, validation and finalization.
- Boxes overwrite a stable R2 key before the conditional D1 save. A failed save can alter assets for an older revision. Use immutable keys. Actual binding is PHOTOS, not STUDIO_ASSETS. Created identity is hard-coded to author.

### export_variorum_d1.py

- Reads nonexistent tables and writes archive/data/versions.json rather than current canonical source. Requires a deliberate adapter, not installation unchanged.
- Missing source lines become empty strings. Stale typeset text is automatically re-materialized even without --re-materialize, contrary to author-controlled correction.
- --re-materialize bypasses rejection of older incoming composite revisions. Preserve revision ordering independently of render operations; photographed composites stay frozen.
- Two output files are written separately, so an interrupted export can mix revisions. Backups and dry-run are useful but do not make the export atomic.

### check_parts.py

- Missing files default to empty inputs; an empty archive returns PASS with zero items. A wrong CI path can silently bypass validation. Require real mandatory inputs and schema.
- Release classification reads bucket/sort instead of pool; verification assumes an unestablished reviews export. Reuse existing release/verification contracts.
- Exposure comparisons reduce records to type/where, losing date/provenance distinctions. Missing fingerprints are not required for typeset composites. Glyph eligibility is not enforced here.

### studio_variorum_builder.js

- Requires a bundle adapter absent from current Studio and seeds invented p001 segmentation when no map exists. Use actual author maps and neutral labels.
- Inserts unescaped source text/labels into innerHTML; use textContent. Selection is mouse-only; add pointer/touch and keyboard support, theme variables and clipboard refusal fallback.
- All composite saves send expected_revision=0. Daily count modulo 26 IDs collide, including across pieces. Use compatible collision-resistant storage IDs and preserve previous revisions.
- assembleBuilderState exempts lyric lines from verification and misses unresolved line IDs. Defaults absent classification to Series via bucket. Incomplete tagging can remain private; release must fail closed on missing evidence.

### typeset_boxes.py

- Without a loaded font, ordinary characters are marked nonfallback and output may claim public_site_eligible=true. fallback_font_path is unused; fallback metrics are heuristics.
- Resolves current source lines instead of frozen materialized text, changing appearance after source corrections without explicit re-materialization.
- Default TTF path does not match supplied OTF/WOFF2. Use actual font metrics, retain whitespace, validate canvas bounds and derive public eligibility in the release gate. Glyph availability alone is insufficient approval.

## Local reproductions

Probes ran against unmodified attachments without remote writes:

1. Draft API request with only an unverified email header, mocked current revision 1 and mocked zero changed rows: HTTP 200, ok=true, revision=2.
2. FontMeasurer() without fonts, synthesize text abc: public_site_eligible=true.
3. check_parts.py --archive-root pointing to an empty temporary directory: exit 0, PASS, all counts zero.

Existing integrity baseline: `python3 tools/check.py` passes, 509 references and 536 checksums. These probes establish draft defects; they do not test live authenticated UI. Source transcription correctness, artifact parity, real iPhone gestures and external lyric availability remain unverified.

## Recommendation

Adapt through canonical source, authenticated vf_docs storage and existing publication fencing. Do not deploy the five drafts unchanged. See [proposed integration design](../superpowers/specs/2026-11-07-variorum-builder-design.md). The author's request authorizes all three tasks; decisions 1–4 explicitly reserved by the attached plan remain pending.
