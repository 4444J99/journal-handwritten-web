# Review studio on Cloudflare (Pages Functions, D1, R2)

The review studio (`studio/index.html`) keeps its state in the claude.ai artifact
database. This directory gives the same collection/document model on the owner's
own Cloudflare account, so the studio no longer depends on the artifact:

| Piece | What it is |
|---|---|
| `functions/_middleware.js` | Runs in front of **every** request, static files included. Verifies the Cloudflare Access JWT itself and fails closed. |
| `functions/api/[[path]].js` | `/api/*` (routing and validation in `lib/api.js`) |
| `functions/_blob/[[id]].js` | `GET /_blob/ID`, streams a photo from R2 |
| `lib/auth.js`, `lib/api.js` | The code behind the functions (plain modules, unit-testable) |
| `schema.sql` | D1 tables `vf_docs` and `vf_revs` (`CREATE TABLE IF NOT EXISTS`, idempotent) |
| `sqlguard.py` | Refuses any generated SQL that touches something other than `vf_` objects (see "The shared database") |
| `../studio/cf-adapter.js` | Defines `window.claude.use('db' / 'user' / 'assets')` over the API, only when the page is not inside claude.ai |
| `import_export.py` | Loads an export directory into D1 (dry run, SQL file, local simulation, remote command printed only) |
| `export_db.py` | The reverse: writes the same per-document layout from `wrangler d1 execute --json` output or a local persist directory |
| `build_dist.py` | Assembles the complete site (page, data, thumbnails **and** full scans) into `dist/` |
| `tests/` | `node:test` and `unittest` suites, see "Tests" |

**Nothing here has been deployed and this lane created no Cloudflare resource
and made no Cloudflare call.** Storage is two existing resources on the owner's
account (author decision, 2026-11-05): the empty D1 database
`studio-documents-prod` (`database_id` `68b1a11f-00a8-4bc7-923b-0931292980c7`,
now in `wrangler.toml`) and the R2 bucket `versforms-studio-assets`. The account
is at its 10-database cap, so no D1 database is created.

## The shared database

`object-lessons-submissions` belongs to another project: it holds that project's
`submissions` table, two indexes on it, and `_cf_KV`, with 0 rows. The studio must
never touch any of that, so:

* every studio object is prefixed `vf_` (`vf_docs`, `vf_revs`), and `schema.sql`
  uses `CREATE TABLE IF NOT EXISTS` and `vf_` names only;
* `sqlguard.py` is a whitelist check on generated SQL. It accepts only
  `CREATE TABLE/INDEX IF NOT EXISTS vf_...`, `INSERT [OR REPLACE] INTO vf_...`,
  `DELETE FROM vf_...` and `SELECT ... FROM vf_...`, and refuses quoted or
  schema-qualified names, `sqlite_*`, `_cf_*`, `DROP`, `ALTER`, `UPDATE` (except
  an upsert's `DO UPDATE`), `ATTACH`, `PRAGMA`, `VACUUM`, triggers and views. String
  literals (the JSON data) are ignored by the scan. `import_export.py` runs it in
  `build_sql`, before anything is written, applied locally or printed for
  `--remote`; `export_db.py` runs it on its query;
* `tests/test_sqlguard.py` proves the guard and scans the studio's own JavaScript
  (`lib/api.js`, `functions/`) and `schema.sql` for any statement on a non-`vf_`
  object.

## Read this before deploying

A Pages deploy creates a public `*.pages.dev` hostname immediately, and the
studio holds private material (transcriptions of unreleased pages, review
decisions, new-version photos). Protection rests entirely on Cloudflare Access
plus the middleware here. That is a decision for the author, and it sits
uneasily with the rule that private content never goes to a public host: an
Access-protected `pages.dev` site is still a public host. Nothing in this
directory claims otherwise. Do not run any deploy command until the Access
application below exists and its policy is confirmed.

## Layout and the exact commands

Pages looks for `functions/` in the directory wrangler is run from, not in the
output directory. So everything is run from `studio-cf/`:

```
cd studio-cf
wrangler pages dev                       # serves ../studio (pages_build_output_dir) with functions/ active
wrangler pages deploy dist --project-name versforms-studio   # real deploy, see "Dashboard steps"
```

`pages_build_output_dir = "../studio"` is what the task asked for and what the
tests run against. **`studio/` alone is not a complete site**: it holds the page,
`data/review.json` and the thumbnails (`img/thumbs/`), but the full-size scans
and spreads the viewer opens (`img/<page>.jpg`, `img/spreads/...`) live once in
`site/img/p` and `site/img/s` and are mapped by `tools/check.py:studio_source`.
Deploying `studio/` would give 404 for every full scan. `build_dist.py` builds the
complete directory (255 files, 0 missing, checked) and the deploy command above
publishes that one:

```
python3 studio-cf/build_dist.py          # writes studio-cf/dist/ (git-ignored)
```

`wrangler pages dev dist` (run from `studio-cf/`) was checked locally: full scans
and thumbnails are served with a valid token and refused without one.

### Network calls of `wrangler pages dev`

Besides the local D1/R2 simulation, `wrangler pages dev` (wrangler 4.104) was seen
making two anonymous requests of its own:

1. Miniflare asks `https://workers.cloudflare.com/cf.json` to fill `request.cf` and
   caches the answer in `.wrangler/cache/cf.json` under the directory it runs in
   (git-ignored here). Switch described below.
2. Wrangler asks `https://api.github.com/repos/cloudflare/skills/contents/skills`
   (a list of agent-skill names) and caches the answer as
   `cloudflare-skills-repo-cache.json` in wrangler's own config directory, even with
   `WRANGLER_SEND_METRICS=false`. This is not a Cloudflare host and carries no studio
   data. No switch for it was found; that is not proof that none exists. In this
   repository's test runs the cache lands in the scratch directory the tests set as
   `XDG_CONFIG_HOME`, not in the repository.

`wrangler pages dev --help` (4.104) has no flag for the first. The
supported switch is the environment variable `CLOUDFLARE_CF_FETCH_ENABLED=false`
(<https://developers.cloudflare.com/workers/wrangler/system-environment-variables/>):
nothing is fetched or cached and a built-in placeholder is used. To keep any cache
out of the repository when fetching stays on, set `MINIFLARE_CACHE_DIR` to a
directory elsewhere. The test helper and `import_export.py --local` set
`CLOUDFLARE_CF_FETCH_ENABLED=false`; for hand-run sessions use
`env CLOUDFLARE_CF_FETCH_ENABLED=false wrangler pages dev`. The studio does not read
`request.cf`, so the placeholder changes nothing.

## Environment variables

| Name | Meaning |
|---|---|
| `ACCESS_TEAM_DOMAIN` | The Zero Trust team domain, e.g. `yourteam.cloudflareaccess.com` (scheme and trailing slash are tolerated). The expected JWT issuer is `https://` + this value; the signing keys come from `https://TEAM_DOMAIN/cdn-cgi/access/certs`. |
| `ACCESS_AUD` | The Access application's AUD tag. |
| `OWNER_EMAILS` | Comma separated; may read and write. |
| `READONLY_EMAILS` | Optional, comma separated; may read. `user.can('data.write')` is false for them, so the studio shows its read-only state. |
| `ACCESS_JWKS_URL_TEST` | **Test hook. Production must never set it.** It is ignored unless the configured team domain host is `localhost` or `127.0.0.1` *and* the override URL's own host is too. |

Missing or malformed `ACCESS_TEAM_DOMAIN`, `ACCESS_AUD` or `OWNER_EMAILS` answers
every request with 503 and no body. A missing, invalid, expired or wrongly
signed token, a wrong `iss`, `aud` or `kid`, an email on no list, or a service
token (no email) answers 403 and no body. Only the signed token matters; nothing
in the request can bypass it.

Unusual paths: the Access check always comes first, so a stranger gets 403 for any
path. For an authenticated caller, a static path no file can have (a NUL or control
character, a segment over 255 bytes, a path over 2048 characters) is answered 404 by the
middleware, and a 502 from the static-file layer (under `wrangler pages dev`, a file used
as a directory such as `/index.html/` made the local simulator answer 502 with a
path-bearing error text; the studio itself never returns 502) is also turned into a
bodyless 404. What the hosted service answers for these paths was not checked.

Paths that leave the served directory: under `wrangler pages dev`, `/..%2fstudio-cf%2fwrangler.toml`
(an encoded slash inside a `..` segment, which the URL parser does not collapse) was served
from one level above `studio/`, for an authenticated caller only. The middleware now
answers a bodyless 404 for any static path with an encoded slash or backslash (`%2f`, `%5c`),
a raw backslash, or a `.` or `..` segment after up to three rounds of decoding. Whether the
hosted service, which serves an uploaded file list, was ever open to this is not known.
Routes are matched without regard to case (`/API/me` reaches the API), so the middleware also
sorts `/api/` and `/_blob/` case-insensitively when it picks the caching header.
Covered by the "unusual paths" and "API path" tests in `tests/server.test.mjs`.

Token rules: exactly three segments; header `alg` must be `RS256` (so `none`
and `HS256` are refused before any key lookup); `kid` required; signature
verified with the JWKS (cached 10 minutes; an unknown `kid` causes at most one
refetch per 30 seconds, which covers key rotation); `iss`, `aud` (string or
array), `exp` (required) and `nbf` (30 s skew) are checked; the email is
compared in lower case.

## API

All responses are `application/json`, `Cache-Control: no-store`.

| Request | Result |
|---|---|
| `GET /api/me` | `{email, canWrite}` |
| `GET /api/db/COLLECTION` | `{rev, docs:[{id,data}]}`; with `?since=REV`, `{rev, changed:false}` when the collection is still at `REV` |
| `GET /api/db/COLLECTION/DOCID` | `{id, data}` or 404 |
| `PUT /api/db/COLLECTION/DOCID` | body = a JSON object up to 64 KiB (counted in bytes); replaces a legacy document, appends an immutable notes/contributions revision; `{ok, rev}` |
| `DELETE /api/db/COLLECTION/DOCID` | `{ok, rev}` for legacy collections; notes/contributions return 409 |
| `POST /api/assets` | raw image body, `Content-Type` `image/jpeg`, `image/png`, `image/webp`, `image/gif` or `image/heic`, up to 15 MiB; the first bytes must match the type; `201 {id}` |
| `GET /_blob/ID` | the stored photo, stored content type, `Cache-Control: private, max-age=31536000, immutable` |

Collections: `reviews decisions versions release batches rconfig notes contributions`. Document ids
match `^[A-Za-z0-9_.-]{1,128}$` (`.` and `..` alone are also refused). Each
collection has a `rev` that rises by one in the same D1 batch (one transaction)
as every new write; a deleted legacy document also bumps it, so polling needs no tombstones.
Writes need `canWrite`, and a browser write must be same-origin
(`Sec-Fetch-Site` / `Origin` are checked when present).

### Immutable notes and contribution revisions (T05)

`notes/{revisionId}` and `contributions/{revisionId}` use the existing tables.
Their minimal envelope must identify schema version 1, the correct family, a
record ID, a matching revision ID, and parent revision IDs. The content model
performs the full document/graph/source validation before browser or backup-CLI
writes. The generic API/importer is not a publication validator.

The API inserts a new revision in one D1 batch. A semantically identical retry
(including JSON object key reordering) succeeds without changing its timestamp
or collection revision. Different content under the same ID and any DELETE
return 409. The six original collections retain replacement/deletion behavior.
The importer similarly refuses a changed revision ID; its SQL uses read-only
`json_tree(...)` to compare JSON values, the sole non-table source admitted by
the SQL guard. A restore can add a prefix before a later collision or failure;
it is resumable and does not erase history, but is not a file-wide transaction.

See [notes workflow and migration](../docs/notes-workflow.md) and the
[integration handoff](../docs/integration/t05-handoff.md). The Cloudflare path
is verified locally; packaging and conditional-write behavior of the original
Claude artifact backend remain separate integration checks.

Upload types follow the page's own code: the file inputs use `accept="image/*"`, and
`toUploadable()` in `studio/index.html` sends `image/jpeg`, `image/png`, `image/webp`
and `image/gif` unchanged (when under 6 MiB) and re-encodes anything else (and
anything larger) to `image/jpeg`. The server allow-list therefore contains those four
(GIF must start with `GIF87a` or `GIF89a`); `image/heic` is kept for direct API
clients, the page never sends it. Anything else answers 415, which the adapter maps to
the page's "Unsupported image type." message.

## The adapter

`studio/cf-adapter.js` is loaded with one plain `<script src="cf-adapter.js">`
before the page's main script (the only edit to `studio/index.html`). It does
nothing when `window.claude.use` already exists. `use()` returns a promise and
rejects when `/api/me` fails (so the page shows its "not saving" state).
`onSnapshot` polls about every 4 s with exponential backoff (cap 60 s), pauses
while the tab is hidden, polls at once after the page's own write, shares one
poller per collection, returns an unsubscribe function, delivers a first
snapshot even for an empty collection, and keeps the last snapshot through
transient failures. It calls the error callback only for terminal errors (401
`revoked`, 403 `not_granted`) or when the very first three polls all fail
(`unavailable`), then drops that listener so the page's own retry does not
create duplicate pollers.

## Importing the existing data

```
python3 studio-cf/import_export.py EXPORT_DIR --dry-run
python3 studio-cf/import_export.py EXPORT_DIR --sql-out /path/outside/repo/import.sql
python3 studio-cf/import_export.py EXPORT_DIR --local /path/to/persist-dir      # local simulation only
python3 studio-cf/import_export.py EXPORT_DIR --sql-out import.sql --remote     # prints the command, never runs it
```

For `exports/studio-db-2026-11-05` the dry run reports `reviews 38` and 0 for
the other five collections, 0 rejects. The SQL contains the schema, one `rev`
bump per collection that receives documents, and `INSERT OR REPLACE` per
document (JSON written pure ASCII, quotes doubled). The importer refuses NaN,
Infinity and -Infinity (and a number such as `1e999`, which Python reads as infinity): JSON cannot hold
them, and one such stored row would make the API's `JSON.parse` fail for every read of that
collection. Re-running replaces the same rows and bumps `rev` once more. Under this host's Node, `wrangler d1 execute
--local` prints its result and then does not exit, so `--local` stops it once it
has reported success.

## Exporting the data

```
python3 studio-cf/export_db.py --from-json docs.json --dry-run          # counts only
python3 studio-cf/export_db.py --from-json docs.json --out /path/to/export-DATE
python3 studio-cf/export_db.py --local /path/to/persist-dir --out /path/to/export-DATE
```

`docs.json` is the output of (run by the author, after `wrangler login`):

```
env -u XDG_CONFIG_HOME wrangler d1 execute object-lessons-submissions --remote --json --command "SELECT collection, id, data FROM vf_docs ORDER BY collection, id" > docs.json
```

The output has the layout of `exports/studio-db-2026-11-05`: `COLLECTION/DOCID.json`,
one document per file (2-space indent, characters not escaped, one trailing newline,
keys in stored order), no folder for an empty collection, and a `README.md` with
per-collection counts. `--local` opens the SQLite file of a wrangler persist directory
read-only (the one that has a `vf_docs` table; it never modifies it). `--out` needs a
directory that does not exist or is empty, so nothing is ever overwritten or deleted.
Invalid rows (unknown collection, bad id, not an object, NaN or Infinity, over 64 KiB,
duplicate) are rejects that block writing unless `--skip-rejects`. The 64 KiB limit is measured on the
compact JSON, the way the API measures a document, not on the pretty-printed file (a document the API
accepts can be well over 64 KiB once indented). `tests/test_export_db.py` proves
`import_export.py` followed by `export_db.py` reproduces the original files byte for
byte (synthetic documents with quotes, newlines and non-ASCII text; and, when the PR 73
export is present in scratch, its 38 real files).

## Run the workbench locally (no Cloudflare)

```
node studio-cf/demo.mjs        # then open http://127.0.0.1:8790/ ; Ctrl-C stops it
```

This runs the real studio page, Pages Functions and API on `wrangler pages dev` with a
**local** D1/R2 simulation, loaded from the committed exports (`exports/studio-db-2026-11-05`
and `exports/derived-decisions-2026-11-05`). A small proxy on 127.0.0.1 adds a freshly
signed **test** token for `owner@demo.test`, because a browser cannot send the Access
header; that token stands in for Cloudflare Access and is not access control, so never
expose the port beyond this machine. Nothing talks to Cloudflare and the real database is
never touched. What you click is kept in `studio-cf/.demo-state/` (git-ignored) between
runs; delete that folder to start again from the exports. Needs node, python3 and wrangler;
`DEMO_PORT`, `DEMO_STATE` and `WRANGLER_BIN` override the port, the state folder and the
wrangler used. First-run setup is complete only when `.demo-state/initialized` exists; an
interrupted first run is repaired by the next launch (the imports are idempotent).
The proxy (`demo-proxy.mjs`) refuses any Host other than its own (421), translates only its
own origin to the upstream's so the API's same-origin check passes for the page's own writes,
and forwards any other Origin unchanged so the API still rejects it; `tests/demo-proxy.test.mjs`
covers each rule. It was run on 2026-11-05: `/api/me` answered the demo owner with write
access, the page loaded all six collections, showed 38 reviewed lines on the first piece, and
the two derived decisions appeared in the Decisions tab. Writes from the page itself were
checked in a browser: undoing one line's review took the server from 38 to 37 documents and
confirming it again took it back to 38, each shown as "Saved".

## wrangler and your login

The author runs `wrangler login` himself; this lane never does. Afterwards wrangler
may need `env -u XDG_CONFIG_HOME` in front of the command to see the legacy config at
`~/Library/Preferences/.wrangler`, where that login is kept, if `XDG_CONFIG_HOME` is
set in the shell (the lane's tests set it to a scratch directory so nothing is written
to the internal disk). So run the real commands as

```
env -u XDG_CONFIG_HOME wrangler d1 execute object-lessons-submissions --remote ...
```

Verified on 2026-11-05, after the author's `wrangler login`: in a shell with
`XDG_CONFIG_HOME=~/.config`, `wrangler whoami`, `wrangler d1 execute object-lessons-submissions
--remote --file ...` and `wrangler pages project create versforms-studio` all worked
**without** the prefix. Use the prefix only if wrangler answers "Not logged in".

## Dashboard steps (do them in this order)

State on 2026-11-05 (the first three steps were run by the lead session after the author's
`wrangler login`; nothing is deployed):

- **Step 1 done:** the empty Pages project `versforms-studio` exists with no deployment.
- **Step 2 done:** the R2 bucket `versforms-studio-assets` exists (created through the
  Cloudflare connector); the D1 database is the shared `object-lessons-submissions`.
- **Step 3 done, and step 10 done early:** `vf_docs` and `vf_revs` were created and the 38
  reviews (41 queries) and the two derived decisions (5 queries) were imported, then read
  back with separate queries (reviews 38, decisions 2, one revision row each; the other
  project's `submissions` table untouched at 0 rows). The import was run before the Access
  policy because nothing can read the database yet: no route is deployed. The rows can be
  removed with `DELETE FROM vf_docs; DELETE FROM vf_revs;`.
- **Remaining:** steps 4 to 9 (the Access application, the variables, the deploy) and the
  step 11 check. Steps 4 to 6 are the author's click-through; the rest can then be run.

1. Create the Pages project **empty**, with no deployment:
   `wrangler pages project create versforms-studio --production-branch main`.
2. The storage already exists: the D1 database `object-lessons-submissions`
   (shared, see "The shared database"; its `database_id` is already in
   `wrangler.toml`) and the R2 bucket `versforms-studio-assets`. Create nothing.
   When `pages_build_output_dir` is present, Cloudflare
   treats `wrangler.toml` as the source of truth for the project's bindings
   (<https://developers.cloudflare.com/pages/functions/wrangler-configuration/>),
   so the D1 and R2 bindings (`DB`, and `PHOTOS` for the bucket, because
   `ASSETS` is reserved by Pages) come from it. Check them under the project's
   **Settings > Bindings** after the first deploy.
3. Apply the schema (only `CREATE TABLE IF NOT EXISTS vf_...`; it leaves the other
   project's `submissions` table alone):
   `env -u XDG_CONFIG_HOME wrangler d1 execute object-lessons-submissions --remote --cwd studio-cf --file studio-cf/schema.sql`.
4. Zero Trust > Access controls > Applications > create a new application,
   **Self-hosted**, name it `versforms-studio`. Add **both** public hostnames:
   `versforms-studio.pages.dev` **and** `*.versforms-studio.pages.dev`
   (production and previews).
5. Add one policy: action **Allow**, include **Emails** equal to the owner
   address only. No Bypass policy, no Everyone rule, no other includes.
   (Optional, outside these steps: someone who should only look needs both an
   Allow include in this policy and an entry in `READONLY_EMAILS`.)
6. Save. On the application's overview copy the **Application Audience (AUD)
   Tag**. Your team domain is `<team>.cloudflareaccess.com`
   (the team name is under Zero Trust > Settings; not re-checked in the dashboard).
7. Set the three variables on the Pages project (Settings > Variables and
   Secrets, production **and** preview): `ACCESS_TEAM_DOMAIN`, `ACCESS_AUD`,
   `OWNER_EMAILS`. UNVERIFIED: whether plain dashboard variables survive when
   `wrangler.toml` is the source of truth. If they do not appear after the first
   deploy, set each with `wrangler pages secret put NAME --project-name
   versforms-studio` instead (secrets are not part of the config file). Do not
   put the owner's address in `wrangler.toml`. Never set `ACCESS_JWKS_URL_TEST`.
8. Do **not** switch on the Pages project's "Enable access policy" toggle. Per
   Cloudflare's documentation it creates its own Access policy/application for the
   preview deployments (see "What the Pages Access toggle covers"). That it has a
   different AUD from the application in step 4, so that a token issued for one is
   refused (403) by the middleware under the other's hostname, is
   **UNVERIFIED**: no Cloudflare documentation page found states it, and no
   account was touched. The step stays because the self-hosted application in
   step 4 already covers the preview hostnames.
9. Only now deploy: `python3 studio-cf/build_dist.py`, then from `studio-cf/`
   `wrangler pages deploy dist --project-name versforms-studio`.
10. Import the data: `python3 studio-cf/import_export.py EXPORT_DIR --sql-out import.sql --remote`,
    then run the command it prints, with `env -u XDG_CONFIG_HOME` in front if
    wrangler does not see your login.
11. Verify: with no session, `curl -i https://versforms-studio.pages.dev/` and
    `.../api/me` and `.../data/review.json` must be answered by the Access login
    (a redirect to `cloudflareaccess.com`), never by studio content. Then open
    the site signed in as the owner. A 403 with an empty body after signing in
    means the middleware refused the token (check `ACCESS_AUD`,
    `ACCESS_TEAM_DOMAIN`, the email); a 503 means a variable is missing.
    UNVERIFIED until deployed: that the Pages-generated `_routes.json` sends
    static files through the middleware (it did in `wrangler pages dev`).

### What the Pages Access toggle covers

Checked against Cloudflare's documentation: the project-level **Settings >
General > Enable access policy** protects **only preview deployments**
(`<hash>.<project>.pages.dev` and branch aliases), "and not your `*.pages.dev`
domain or custom domain" — <https://developers.cloudflare.com/pages/configuration/preview-deployments/>.
Extending it to the production `*.pages.dev` hostname needs the manual steps in
<https://developers.cloudflare.com/pages/platform/known-issues/#enable-access-on-your-pagesdev-domain>.
The same pages describe the toggle as creating an Access policy for the preview
deployments, and the known-issues page tells you to edit the application it creates
under **Access > Applications**; they do not say what AUD that application has
(UNVERIFIED). That is why steps 4 and 5 make one self-hosted application covering both
hostnames. The middleware is a second line of defence and stays either way.

## Tests

```
node --test --test-concurrency=1 studio-cf/tests/*.test.mjs
python3 -m unittest discover -s studio-cf/tests -p 'test_*.py'
```

* `server.test.mjs`: boots `wrangler pages dev` (local D1 and R2 simulation, test
  variables passed with `--binding`, so no `.dev.vars` file is written anywhere),
  signs tokens with a throwaway RSA key, serves a local JWKS, and checks that all
  nine routes answer 403 with an empty body for each bad token class; then CRUD,
  rev, `?since`, validation, limits, assets, read-only.
* `auth.unit.test.mjs`, `adapter.unit.test.mjs`: unit tests (fake fetch, fake clock).
* `import-local.test.mjs`: `import_export.py --local` then the API reads the same database.
* `browser-smoke.test.mjs`: real page in headless Google Chrome through the adapter
  (skipped visibly if Chrome is absent).
* `test_import_export.py`: parsing, rejects, escaping (round trip through sqlite3), counts.
* `test_sqlguard.py`: the vf_-only guard and a scan of the studio's own SQL.
* `test_export_db.py`: `export_db.py` and the byte-for-byte round trip with the importer.

Test files, wrangler logs and persisted state go to `STUDIO_CF_SCRATCH` (default
`/Volumes/Archive4T/Temporary/versforms-work/studio-cf`).

## Publish from the Studio

Release > Calendar provides Publish and Publication history. The first destination is Staging. The browser builds the complete candidate in a module worker; the server independently verifies its exact piece/version selection, line readings, source bindings, withheld blocks, page geometry, metadata and file list before preview is available. Confirm names the previewed SHA-256. Copy and verification run in bounded requests; immutable content-addressed images are reused. The only mutable public object is current.json, changed conditionally against the previous pointer. Prepared/committed audit records allow a retry to complete the appearance record after a pointer move. Only newly added poems receive a new site appearance; staging never consumes an as-posted production number.

The compiler lives in studio/publish-compiler.mjs, re-exported by lib/publish.js for Functions. The Python posting path remains supported and honors a recorded decisions/gruw-policy choice of exactly skip. Series, verification and filing are the only overridable gates; Reserve/Archive/unknown pools, stale reviews, leaks and unchecked shared scans remain hard stops.

### Build and bindings

From the repository root:

~~~sh
python3 studio-cf/build_dist.py
python3 studio-cf/build_reader.py --out .post-poem-work/reader-package
~~~

Reader output must be new or empty. The reader package is reviewed into 4444J99/versforms. It contains the blank shell, approved pinned engine, read-only R2 function and standalone staging configuration; it contains no private source data or scans. Staging must retain its own package/library root: local Pages compilation otherwise resolves the parent production configuration.

Studio needs DB, PHOTOS, STAGING=versforms-staging, PUBLIC=versforms-public, PUBLISH_BUILD_MODE=browser and the exact PUBLISH_SHELL_SHA256 from dist/publish/pin.json. Existing ACCESS_AUD, ACCESS_TEAM_DOMAIN and OWNER_EMAILS remain dashboard-owned secrets. Fail closed remains enabled. The public project binds only PUBLIC=versforms-public; staging binds only PUBLIC=versforms-staging. Raw R2 public access is unnecessary.

For the Git-connected Studio build, set the project root to studio-cf, output to dist, and build command python3 -m pip install -r requirements-build.txt && python3 build_cloudflare.py. The project root must contain functions/ so the authentication middleware is compiled (https://developers.cloudflare.com/pages/functions/get-started/). The wrapper selects the hosted interpreter rather than this Mac's font venv. Exact package versions are pinned to those used for the approved shell. Cloudflare's supported Python build runtimes are documented at https://developers.cloudflare.com/pages/configuration/build-image/. A different shell hash fails closed; it is not silently accepted.

Atlas tiles preserve the original decoded pixels as PNG bytes, served with image/png under the engine's existing .jpg routes. The engine already supports multiple atlas textures. No Pillow/fontTools work runs on a Publish tap. Source fragments, the source catalogue and all unpublished assets are behind Access in the Studio deployment.

### Verification and limits

~~~sh
python3 tools/check.py
node --test studio-cf/tests/publish.unit.test.mjs studio-cf/tests/publish-storage.unit.test.mjs studio-cf/tests/public-reader.unit.test.mjs studio-cf/tests/publish-client.unit.test.mjs
node --test studio-cf/tests/publish-local.test.mjs
python3 studio-cf/verify_publish_parity.py --db EXPORT_DIR --piece p001
python3 tools/ci_local.py
~~~

The local integration test builds its own checkout assets in a unique scratch directory and uses local-only review confirmations, D1 and R2. It does not alter the hosted author's reviews. Node's built-in sqlite module is used by storage unit tests. Real-export parity compares canonical JSON in one shared JavaScript numeric model (Python's 1.0 and JavaScript's 1 represent the same JSON number), all non-atlas file hashes and exact tile pixels/line geometry. The source compiler still refuses stale transcripts.

The original hosted server-build spike used 24 ms CPU for one published page and 166 ms for 123 synthetic pages. The free fallback splits verification and image copying across requests. Synthetic worst-case bounded traces passed, with warm checks around 3-8 ms and occasional cold checks at 11 ms. This is measured evidence, not a guarantee against Cloudflare CPU exhaustion; no billing plan was changed. An interrupted operation is retried using the same candidate hash, or rebuilt when source revisions changed.

The first real p001 confirmation and physical iPhone/laptop acceptance remain author actions. The live source selects V[0]; five author corrections currently reside on unpublished versions. The preview reports that distinction.

Final confirmation and rollback share a non-expiring D1 fence with Studio source writes. Recovery first changes the R2 pointer ETag before releasing an abandoned fence, preventing a delayed upload from publishing after a source edit. Source writes return 409 during that short final operation; opening Publication history completes recovery. Only committed publication receipts appear as rollback targets.

### Prevent raw-source deployment

The repository's site/ directory is private source. Its _worker.js deliberately returns 403 on Pages, including for data and images. Deploy Studio only from studio-cf/dist with its authenticated Functions; deploy readers only from the reviewed public reader package. The raw-source guard must not be copied into either generated output.

Staging uses the public package's staging/ project directory and site/ output, with PUBLIC bound only to versforms-staging. Do not connect it to the private journal-handwritten-web repository or deploy that repository's top-level site/. The owner acceptance check exposed such a Dashboard connection; automatic Git deployments were disabled and the correct reader restored. Keep source, build root and uses_functions in the remote verification receipt, not only the commit label.
