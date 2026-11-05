// Minimal Chrome DevTools Protocol client over a WebSocket (global WebSocket, Node >= 22, no npm packages).
//
// Two properties the verifier depends on:
//   * every command has a time limit, and
//   * when the socket closes or errors (Chrome crashed, was killed, or dropped the connection), every command that
//     is still waiting is rejected at once and later commands are rejected without being sent.
// Without them a Chrome crash leaves the verifier waiting for answers that can never arrive.
//
// `ws` is anything with addEventListener / send / close (a browser-style WebSocket); the tests pass a fake.

export const DEFAULT_COMMAND_TIMEOUT_MS = 30000;

export class CDP {
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

  static async connect(url, opts) {
    const ws = new WebSocket(url);
    await new Promise((res, rej) => {
      ws.addEventListener("open", res, { once: true });
      ws.addEventListener("error", () => rej(new Error("websocket error")), { once: true });
    });
    return new CDP(ws, opts);
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

// Write `text` to `stream` and exit with `code` only once the data has been handed to the operating system.
// process.exit() straight after process.stdout.write() can cut a large report short when stdout is a pipe.
export function writeThenExit(stream, text, code, exit = process.exit) {
  let done = false;
  const finish = () => { if (!done) { done = true; exit(code); } };
  try { stream.write(text, finish); } catch { finish(); }
}
