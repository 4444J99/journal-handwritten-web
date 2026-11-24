import test from "node:test";
import assert from "node:assert/strict";
import {
  createReadProgress,
  computeDraftPages,
  READ_KEY,
  READ_ENABLED_KEY,
  DWELL_MS,
} from "../site/read-progress.mjs";

const ORDER = ["diary1-0", "diary1-1", "diary2-0", "diary2-1"];

function memStore(seed = {}) {
  const map = new Map(Object.entries(seed));
  return {
    map,
    get(k) {
      return map.has(k) ? map.get(k) : null;
    },
    set(k, v) {
      map.set(k, v);
    },
  };
}

test("read rule: a glance does not mark read, a dwell does", () => {
  const rp = createReadProgress({ store: memStore(), order: ORDER, dwellMs: 2500 });
  assert.equal(rp.noteHeld("diary1-0", 2499), false);
  assert.equal(rp.isRead("diary1-0"), false);
  assert.equal(rp.noteHeld("diary1-0", 2500), true);
  assert.equal(rp.isRead("diary1-0"), true);
  assert.equal(rp.noteHeld("diary1-0", 99999), false); // already read: no second mark
});

test("a page turned away from counts as read", () => {
  const rp = createReadProgress({ store: memStore(), order: ORDER });
  assert.equal(rp.noteTurned("diary1-1"), true);
  assert.equal(rp.isRead("diary1-1"), true);
  assert.equal(rp.readCount(), 1);
});

test("ids outside the notebook order are never stored", () => {
  const rp = createReadProgress({ store: memStore(), order: ORDER });
  assert.equal(rp.markRead("render-v1"), false);
  assert.equal(rp.markRead(null), false);
  assert.equal(rp.markRead(undefined), false);
  assert.deepEqual(rp.readIds(), []);
});

test("persistence: a stored set round-trips in notebook order", () => {
  const store = memStore();
  const first = createReadProgress({ store, order: ORDER });
  first.markRead("diary2-1");
  first.markRead("diary1-0");
  assert.equal(store.get(READ_KEY), JSON.stringify(["diary1-0", "diary2-1"]));
  const second = createReadProgress({ store, order: ORDER });
  assert.deepEqual(second.readIds(), ["diary1-0", "diary2-1"]);
  assert.equal(second.readCount(), 2);
});

test("persistence: a corrupt or misshapen value reads as empty, never throws", () => {
  for (const bad of ["{not json", "[1,2]", "\"diary1-0\"", "42", ""]) {
    const rp = createReadProgress({ store: memStore({ [READ_KEY]: bad }), order: ORDER });
    assert.deepEqual(rp.readIds(), [], bad);
  }
  const throwing = { get() { throw new Error("denied"); }, set() { throw new Error("denied"); } };
  const rp = createReadProgress({ store: throwing, order: ORDER });
  assert.equal(rp.markRead("diary1-0"), true); // in-memory mark still works
  assert.deepEqual(rp.readIds(), ["diary1-0"]);
});

test("off switch: no recording while off, stored set kept, resume on re-enable", () => {
  const store = memStore();
  const rp = createReadProgress({ store, order: ORDER });
  rp.markRead("diary1-0");
  assert.equal(rp.setEnabled(false), false);
  assert.equal(store.get(READ_ENABLED_KEY), "0");
  assert.equal(rp.markRead("diary1-1"), false);
  assert.equal(rp.noteTurned("diary1-1"), false);
  assert.equal(rp.noteHeld("diary1-1", 99999), false);
  assert.equal(rp.isRead("diary1-0"), true); // the stored set is not erased
  assert.equal(rp.setEnabled(true), true);
  assert.equal(store.get(READ_ENABLED_KEY), "1");
  assert.equal(rp.markRead("diary1-1"), true); // resumes from the stored set
  const reloaded = createReadProgress({ store, order: ORDER });
  assert.equal(reloaded.isEnabled(), true);
  assert.deepEqual(reloaded.readIds(), ["diary1-0", "diary1-1"]);
});

test("off switch: a stored off flag loads as disabled", () => {
  const rp = createReadProgress({
    store: memStore({ [READ_ENABLED_KEY]: "0" }),
    order: ORDER,
  });
  assert.equal(rp.isEnabled(), false);
});

test("next/previous walk notebook order and stop at the ends, never wrap", () => {
  const rp = createReadProgress({ store: memStore(), order: ORDER });
  assert.equal(rp.nextId("diary1-0"), "diary1-1");
  assert.equal(rp.prevId("diary1-1"), "diary1-0");
  assert.equal(rp.nextId("diary2-1"), null);
  assert.equal(rp.prevId("diary1-0"), null);
  assert.equal(rp.nextId("not-a-page"), null);
  assert.equal(rp.prevId("not-a-page"), null);
  assert.equal(rp.nextId(null), null);
});

test("draft pages: only lines from a non-current version mark the page", () => {
  const pages = [{ id: "diary1-0" }, { id: "diary1-1" }, { id: "diary2-0" }];
  const lines = [
    { pi: 0, ver: 0 },
    { pi: 0, ver: 1 }, // draft line on diary1-0
    { pi: 1, ver: 0 },
    { pi: 2, ver: 3 }, // draft line on diary2-0
    { pi: 9, ver: 2 }, // no such page: ignored
    { pi: 1 }, // no ver: ignored
  ];
  assert.deepEqual([...computeDraftPages(lines, pages)].sort(), ["diary1-0", "diary2-0"]);
  assert.deepEqual([...computeDraftPages([], pages)], []);
  assert.deepEqual([...computeDraftPages(null, pages)], []);
  assert.deepEqual([...computeDraftPages(lines, null)], []);
});

test("dwell default is a short hold", () => {
  assert.equal(DWELL_MS, 2500);
  const rp = createReadProgress({ store: memStore(), order: ORDER });
  assert.equal(rp.dwellMs, 2500);
});
