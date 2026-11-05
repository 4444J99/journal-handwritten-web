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
| `schema.sql` | D1 tables `docs` and `revs` (idempotent) |
| `../studio/cf-adapter.js` | Defines `window.claude.use('db' / 'user' / 'assets')` over the API, only when the page is not inside claude.ai |
| `import_export.py` | Loads an export directory into D1 (dry run, SQL file, local simulation, remote command printed only) |
| `build_dist.py` | Assembles the complete site (page, data, thumbnails **and** full scans) into `dist/` |
| `tests/` | `node:test` and `unittest` suites, see "Tests" |

**Nothing here has been deployed and no Cloudflare resource has been created.**
The D1 database and the R2 bucket do not exist yet, so `wrangler.toml` has no
`database_id` (it only exists after `wrangler d1 create`).

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
| `PUT /api/db/COLLECTION/DOCID` | body = a JSON object up to 64 KiB (counted in bytes); replaces the document; `{ok, rev}` |
| `DELETE /api/db/COLLECTION/DOCID` | `{ok, rev}` |
| `POST /api/assets` | raw image body, `Content-Type` `image/jpeg`, `image/png`, `image/webp` or `image/heic`, up to 15 MiB; the first bytes must match the type; `201 {id}` |
| `GET /_blob/ID` | the stored photo, stored content type, `Cache-Control: private, max-age=31536000, immutable` |

Collections: `reviews decisions versions release batches rconfig`. Document ids
match `^[A-Za-z0-9_.-]{1,128}$` (`.` and `..` alone are also refused). Each
collection has a `rev` that rises by one in the same D1 batch (one transaction)
as every write; a deleted document also bumps it, so polling needs no tombstones.
Writes need `canWrite`, and a browser write must be same-origin
(`Sec-Fetch-Site` / `Origin` are checked when present).

Known gap against the artifact: the page's `toUploadable()` passes `image/gif`
through unchanged, and the allow-list above has no GIF, so a GIF upload is now
refused (`unsupported_type`, "Unsupported image type.").

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
document (JSON written pure ASCII, quotes doubled). Re-running replaces the same
rows and bumps `rev` once more. Under this host's Node, `wrangler d1 execute
--local` prints its result and then does not exit, so `--local` stops it once it
has reported success.

## Dashboard steps (do them in this order)

The Cloudflare account work below is the author's; nothing was run.

1. Create the Pages project **empty**, with no deployment:
   `wrangler pages project create versforms-studio --production-branch main`.
2. Create the storage:
   `wrangler d1 create versforms-studio`, then `wrangler r2 bucket create versforms-studio-assets`.
   Paste the printed D1 `database_id` into `[[d1_databases]]` in `wrangler.toml`
   (the id is not a secret). When `pages_build_output_dir` is present, Cloudflare
   treats this file as the source of truth for the project's bindings
   (<https://developers.cloudflare.com/pages/functions/wrangler-configuration/>),
   so the D1 and R2 bindings (`DB`, and `PHOTOS` for the bucket, because
   `ASSETS` is reserved by Pages) come from it. Check them under the project's
   **Settings > Bindings**. UNVERIFIED: whether `wrangler pages deploy` would
   create missing resources automatically when `database_id` is omitted.
   Automatic provisioning is documented for Workers (`wrangler deploy`, 4.45.0
   and later), not for Pages, so do not rely on it.
3. Apply the schema: `wrangler d1 execute versforms-studio --remote --cwd studio-cf --file studio-cf/schema.sql`.
4. Zero Trust > Access controls > Applications > create a new application,
   **Self-hosted**, name it `versforms-studio`. Add **both** public hostnames:
   `versforms-studio.pages.dev` **and** `*.versforms-studio.pages.dev`
   (production and previews).
5. Add one policy: action **Allow**, include **Emails** equal to the owner
   address only. No Bypass policy, no Everyone rule, no other includes. (Add a
   second address to `READONLY_EMAILS` and to the policy only if someone should
   be able to look.)
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
8. Do **not** switch on the Pages project's "Enable access policy" toggle. It
   creates its own, separate Access application with a different AUD, so one of
   the hostnames would then carry a token the middleware rejects (403).
9. Only now deploy: `python3 studio-cf/build_dist.py`, then from `studio-cf/`
   `wrangler pages deploy dist --project-name versforms-studio`.
10. Import the data: `python3 studio-cf/import_export.py EXPORT_DIR --sql-out import.sql --remote`,
    then run the command it prints.
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
That is why steps 4 and 5 make one self-hosted application covering both
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

Test files, wrangler logs and persisted state go to `STUDIO_CF_SCRATCH` (default
`/Volumes/Archive4T/Temporary/versforms-work/studio-cf`).
