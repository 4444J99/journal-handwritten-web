/* Review studio storage adapter for Cloudflare (Pages Functions + D1 + R2).
 *
 * Defines window.claude.use('db' | 'user' | 'assets') with the same shape the
 * studio page uses inside claude.ai, backed by /api/*. It does nothing when
 * window.claude already provides use(), so the page still runs inside claude.ai.
 *
 * Reads are polled (about every 4 s, exponential backoff on failure, paused
 * while the tab is hidden, immediate poll after the page's own write).
 */
(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined' && root === window) {
    if (!(window.claude && typeof window.claude.use === 'function')) {
      var env = {
        fetch: function (u, o) { return window.fetch(u, o); },
        setTimeout: function (f, ms) { return window.setTimeout(f, ms); },
        clearTimeout: function (t) { window.clearTimeout(t); },
        random: Math.random,
        isHidden: function () { return document.hidden; },
        onVisible: function (cb) { document.addEventListener('visibilitychange', function () { if (!document.hidden) cb(); }); },
      };
      window.claude = Object.assign(window.claude || {}, { use: api.createAdapter(env).use });
    }
  }
})(typeof window !== 'undefined' ? window : this, function () {
  'use strict';

  var COLLECTIONS = ['reviews', 'decisions', 'versions', 'release', 'batches', 'rconfig', 'notes', 'contributions', 'artifacts', 'parts', 'composites'];
  var POLL_MS = 4000;
  var MAX_BACKOFF_MS = 60000;
  var INITIAL_FAILURES_BEFORE_ERROR = 3;

  function err(code, message, status) {
    var e = new Error(message || code);
    e.code = code;
    if (status !== undefined) e.status = status;
    return e;
  }

  // Status to the error codes the studio page checks for database calls.
  function dbCode(status) {
    if (status === 401) return 'revoked';
    if (status === 403) return 'not_granted';
    if (status === 409) return 'conflict';
    if (status === 429) return 'resource_exhausted';
    if (status === 507) return 'quota_exceeded';
    if (status === 400 || status === 413) return 'invalid_argument';
    if (status >= 500) return 'unavailable';
    return 'invalid_argument';
  }

  // Status to the error codes the studio page checks for uploads.
  function assetCode(status) {
    if (status === 401 || status === 403) return 'not_granted';
    if (status === 413) return 'too_large';
    if (status === 415) return 'unsupported_type';
    if (status === 429) return 'rate_limited';
    if (status === 507) return 'quota_or_state';
    if (status >= 500) return 'store_unavailable';
    return 'unsupported_type';
  }

  function clone(v) { return JSON.parse(JSON.stringify(v)); }

  function createAdapter(env) {
    var fetchFn = env.fetch;
    var rnd = env.random || Math.random;
    var meCache = null;

    // One request. Network failure and a redirect to the Access login are mapped
    // by the caller's code mapper via `kind`.
    async function request(path, init, mapCode) {
      var res;
      try {
        res = await fetchFn(path, Object.assign({ credentials: 'same-origin', cache: 'no-store', redirect: 'manual' }, init || {}));
      } catch (e) {
        throw err(mapCode(503), 'network error', 0);
      }
      if (res.type === 'opaqueredirect' || (res.status >= 300 && res.status < 400)) throw err(mapCode(401), 'session ended', 401);
      if (!res.ok) throw err(mapCode(res.status), 'HTTP ' + res.status, res.status);
      return res;
    }
    async function requestJson(path, init, mapCode) {
      var res = await request(path, init, mapCode);
      try { return await res.json(); } catch (e) { throw err(mapCode(503), 'bad response', 0); }
    }

    function loadMe() {
      if (meCache) return meCache;
      var p = (async function () {
        var last;
        for (var i = 0; i < 3; i++) {
          try { return await requestJson('/api/me', { method: 'GET' }, dbCode); }
          catch (e) {
            last = e;
            if (e.code !== 'unavailable') break;
            await new Promise(function (r) { env.setTimeout(r, 400 + rnd() * 400); });
          }
        }
        throw last;
      })();
      meCache = p;
      p.catch(function () { if (meCache === p) meCache = null; });
      return p;
    }

    /* ---------------------------------------------------------- polling */
    var pollers = new Map();

    function snapshotOf(docs) {
      var list = docs.map(function (d) {
        return { id: d.id, exists: true, data: function () { return clone(d.data); } };
      });
      return {
        docs: list, size: list.length, empty: list.length === 0,
        forEach: function (f) { list.forEach(f); },
      };
    }

    function getPoller(name) {
      var p = pollers.get(name);
      if (p) return p;
      p = { name: name, listeners: new Set(), rev: null, snap: null, timer: null, inflight: false, again: false, failures: 0, everOk: false };
      pollers.set(name, p);
      return p;
    }

    function schedule(p, ms) {
      if (p.timer !== null) { env.clearTimeout(p.timer); p.timer = null; }
      if (p.listeners.size === 0) return;
      if (env.isHidden()) return; // paused; onVisible() restarts
      p.timer = env.setTimeout(function () { p.timer = null; poll(p); }, ms);
    }
    function nextDelay(p) {
      var base = p.failures ? Math.min(MAX_BACKOFF_MS, POLL_MS * Math.pow(2, p.failures)) : POLL_MS;
      return base * (0.9 + rnd() * 0.2);
    }

    function stop(p) {
      if (p.timer !== null) { env.clearTimeout(p.timer); p.timer = null; }
      pollers.delete(p.name);
    }

    async function poll(p) {
      if (p.listeners.size === 0) { stop(p); return; }
      if (p.inflight) { p.again = true; return; }
      p.inflight = true; p.again = false;
      try {
        var q = '/api/db/' + p.name + (p.rev !== null ? '?since=' + p.rev : '');
        var body = await requestJson(q, { method: 'GET' }, dbCode);
        p.failures = 0; p.everOk = true;
        if (body && body.changed === false && p.snap) {
          // unchanged
        } else if (body && Array.isArray(body.docs)) {
          p.rev = body.rev; p.snap = snapshotOf(body.docs);
          p.listeners.forEach(function (l) { l.deliver(p.snap); });
        }
      } catch (e) {
        var code = e && e.code;
        if (code === 'revoked' || code === 'not_granted' || code === 'invalid_argument' || code === 'quota_exceeded') {
          fail(p, e);
        } else {
          p.failures++;
          if (!p.everOk && p.failures >= INITIAL_FAILURES_BEFORE_ERROR) fail(p, e);
        }
      } finally { p.inflight = false; }
      if (!pollers.has(p.name)) return;
      if (p.again) { p.again = false; poll(p); return; }
      schedule(p, nextDelay(p));
    }

    // Terminal failure: tell every listener once, drop them, stop polling. The
    // page resubscribes if it wants to try again.
    function fail(p, e) {
      var ls = Array.from(p.listeners);
      p.listeners.clear();
      stop(p);
      ls.forEach(function (l) { l.error(e); });
    }

    if (env.onVisible) env.onVisible(function () {
      pollers.forEach(function (p) { if (p.timer === null && !p.inflight) poll(p); });
    });

    function pollNow(name) {
      var p = pollers.get(name);
      if (p && p.listeners.size) { if (p.timer !== null) { env.clearTimeout(p.timer); p.timer = null; } poll(p); }
    }

    /* -------------------------------------------------------------- db */
    function checkColl(name) {
      if (COLLECTIONS.indexOf(name) < 0) throw err('invalid_argument', 'unknown collection');
    }
    function docPath(coll, id) { return '/api/db/' + coll + '/' + encodeURIComponent(id); }

    function collection(name) {
      checkColl(name);
      return {
        id: name,
        doc: function (id) {
          if (typeof id !== 'string' || !id) throw err('invalid_argument', 'bad document id');
          return {
            id: id,
            set: async function (data) {
              await request(docPath(name, id), { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(data) }, dbCode);
              pollNow(name);
            },
            delete: async function () {
              await request(docPath(name, id), { method: 'DELETE' }, dbCode);
              pollNow(name);
            },
            get: async function () {
              try {
                var body = await requestJson(docPath(name, id), { method: 'GET' }, dbCode);
                return { id: id, exists: true, data: function () { return clone(body.data); } };
              } catch (e) {
                if (e.status === 404) return { id: id, exists: false, data: function () { return undefined; } };
                throw e;
              }
            },
          };
        },
        onSnapshot: function (cb, errCb) {
          var p = getPoller(name);
          var listener = {
            deliver: function (snap) { try { cb(snap); } catch (e) { if (typeof console !== 'undefined') console.error(e); } },
            error: function (e) { if (typeof errCb === 'function') { try { errCb(e); } catch (x) { if (typeof console !== 'undefined') console.error(x); } } },
          };
          p.listeners.add(listener);
          if (p.snap) { env.setTimeout(function () { if (p.listeners.has(listener)) listener.deliver(p.snap); }, 0); }
          else if (!p.inflight) poll(p);
          return function unsubscribe() {
            p.listeners.delete(listener);
            if (p.listeners.size === 0) stop(p);
          };
        },
      };
    }

    /* ---------------------------------------------------------- assets */
    var assets = {
      upload: async function (blob, opts) {
        var type = (opts && opts.type) || (blob && blob.type) || '';
        var body = await requestJson('/api/assets', { method: 'POST', headers: { 'content-type': type }, body: blob }, assetCode);
        if (!body || typeof body.id !== 'string') throw err('store_unavailable', 'bad response');
        return { id: body.id };
      },
    };

    var user = {
      can: async function (cap) {
        var me = await loadMe();
        if (cap === 'data.write' || cap === 'assets.write' || cap === 'assets.upload') return !!me.canWrite;
        if (cap === 'data.read' || cap === 'assets.read') return true;
        return false;
      },
    };

    var db = { collection: collection };

    return {
      use: async function (name) {
        if (name === 'db') { await loadMe(); return db; }
        if (name === 'user') { await loadMe(); return user; }
        if (name === 'assets') { await loadMe(); return assets; }
        throw err('capability_disabled', 'unknown capability');
      },
      _pollers: pollers,
    };
  }

  return { createAdapter: createAdapter, dbCode: dbCode, assetCode: assetCode };
});
