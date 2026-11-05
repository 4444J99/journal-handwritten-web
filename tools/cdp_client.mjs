// Minimal Chrome DevTools Protocol client over a WebSocket (global WebSocket, Node >= 22, no npm packages).
//
// Two properties the verifier depends on:
//   * the connection and every command have a time limit, and
//   * when the socket closes or errors (Chrome crashed, was killed, or dropped the connection), every command that
//     is still waiting is rejected at once and later commands are rejected without being sent.
// Without them a Chrome crash leaves the verifier waiting for answers that can never arrive.
//
// `ws` is anything with addEventListener / send / close (a browser-style WebSocket); the tests pass a fake.

export const DEFAULT_COMMAND_TIMEOUT_MS = 30000;
export const DEFAULT_CONNECT_TIMEOUT_MS = 15000;

export class CDP {
  static DEFAULT_CONNECT_TIMEOUT_MS = DEFAULT_CONNECT_TIMEOUT_MS;

  constructor(ws, { timeoutMs = DEFAULT_COMMAND_TIMEOUT_MS } = {}) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    this.handlers = [];
    this.timeoutMs = timeoutMs;
    this.dead = null; // an Error once the connection is gone
    ws.addEventListener("message", ev => {
      let m;
      try { m = JSON.parse(ev.data); } catch { return; }
      if (m.id) {
        const p = this.pending.get(m.id);
        if (!p) return;
        this.pending.delete(m.id);
        clearTimeout(p.timer);
        m.error ? p.rej(new Error(`${p.method}: ${m.error.message}`)) : p.res(m.result);
      } else for (const h of this.handlers) h(m);
    });
    ws.addEventListener("close", () => this.#fail(new Error("DevTools connection closed")));
    ws.addEventListener("error", () => this.#fail(new Error("DevTools connection error")));
  }

  // Opens the connection. The WebSocket handshake has a time limit (connectTimeoutMs, default 15 s): an endpoint that
  // accepts the TCP connection and never answers would otherwise leave the promise pending for ever, and with it
  // everything that waits on it. On timeout the socket is closed and the promise rejects with a clear error; the time
  // limit is cleared as soon as the socket opens or fails, so it can never close a connection that is working.
  // opts: { connectTimeoutMs, timeoutMs (per command, see the constructor), WebSocketImpl (tests only) }
  static async connect(url, { connectTimeoutMs = DEFAULT_CONNECT_TIMEOUT_MS, WebSocketImpl = WebSocket, ...rest } = {}) {
    const ws = new WebSocketImpl(url);
    await new Promise((res, rej) => {
      let timer = null;
      const settle = (fn, arg) => { clearTimeout(timer); fn(arg); };
      timer = setTimeout(() => {
        // reject first: closing a socket that is still connecting fires its 'error' event at once, and the first rejection wins
        rej(new Error(`DevTools connection: no WebSocket handshake within ${connectTimeoutMs} ms`));
        try { ws.close(); } catch {}
      }, connectTimeoutMs);
      ws.addEventListener("open", () => settle(res), { once: true });
      ws.addEventListener("error", () => settle(rej, new Error("websocket error")), { once: true });
      ws.addEventListener("close", () => settle(rej, new Error("websocket closed before it opened")), { once: true });
    });
    return new CDP(ws, rest);
  }

  #fail(err) {
    if (this.dead) return;
    this.dead = err;
    for (const [id, p] of this.pending) {
      clearTimeout(p.timer);
      p.rej(new Error(`${p.method}: ${err.message}`));
      this.pending.delete(id);
    }
  }

  send(method, params = {}, sessionId, timeoutMs = this.timeoutMs) {
    if (this.dead) return Promise.reject(new Error(`${method}: ${this.dead.message}`));
    const id = ++this.id;
    return new Promise((res, rej) => {
      const timer = setTimeout(() => {
        if (this.pending.delete(id)) rej(new Error(`${method}: no answer from Chrome within ${timeoutMs} ms`));
      }, timeoutMs);
      this.pending.set(id, { res, rej, method, timer });
      try {
        this.ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
      } catch (e) {
        clearTimeout(timer);
        this.pending.delete(id);
        rej(new Error(`${method}: ${e.message}`));
      }
    });
  }

  on(h) { this.handlers.push(h); }
  close() { try { this.ws.close(); } catch {} }
}

// Launch a browser, connect to it, run `work(cdp, launched)`, and stop the browser whatever happens: when the
// connection cannot be made, when the work throws, and when it succeeds. A browser that was launched is a process of
// its own (it does not end when this one does) and it holds the profile directory, so every step after the launch
// belongs inside the cleanup scope.
//   launch():       -> { proc, wsUrl }       (proc has kill())
//   connect(wsUrl): -> a CDP (or anything with close())
export async function withBrowser({ launch, connect }, work) {
  let launched = null, cdp = null;
  try {
    launched = await launch();
    cdp = await connect(launched.wsUrl);
    return await work(cdp, launched);
  } finally {
    if (cdp) { try { cdp.close(); } catch {} }
    if (launched && launched.proc) { try { launched.proc.kill("SIGTERM"); } catch {} }
  }
}

// Write `text` to `stream` and exit with `code` only once the data has been handed to the operating system.
// process.exit() straight after process.stdout.write() can cut a large report short when stdout is a pipe.
export function writeThenExit(stream, text, code, exit = process.exit) {
  let done = false;
  const finish = () => { if (!done) { done = true; exit(code); } };
  try { stream.write(text, finish); } catch { finish(); }
}
