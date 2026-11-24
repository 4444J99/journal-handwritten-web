/**
 * Read-progress tracking for the journal reader (journal-handwritten-web #16).
 *
 * Pure module: no DOM, no fetch, no studio-database access. The reader wires
 * it in from site/index.html; the tests exercise it with a fake store.
 *
 * The read unit is one journal page, identified by its j.json page id. A page
 * counts as read when it has been held at readable size for a short dwell
 * (noteHeld) or when the reader turns away from it (noteTurned). "Next" and
 * "previous" walk the notebook order given at construction and stop at the
 * ends instead of wrapping, so the last page stays the last page.
 *
 * Persistence is a versioned localStorage key holding the set of read page
 * ids, through the reader's guarded `store` helper. A corrupt or absent
 * value reads as empty rather than throwing, because a reader must never
 * fail to open over a progress record. Turning tracking off stops recording
 * and hides the marks; turning it back on resumes from the stored set.
 */

export const READ_KEY = "jhw.read.v1";
export const READ_ENABLED_KEY = "jc.readtrack";
export const DWELL_MS = 2500;

export function createReadProgress({
  store = null,
  order = [],
  key = READ_KEY,
  enabledKey = READ_ENABLED_KEY,
  dwellMs = DWELL_MS,
} = {}) {
  const ids = [...order];
  const known = new Set(ids);
  const indexOf = new Map(ids.map((id, i) => [id, i]));
  let enabled = true;
  let read = new Set();

  const load = () => {
    read = new Set();
    if (!store) return;
    let raw = null;
    try {
      raw = store.get(key);
    } catch {
      return;
    }
    if (typeof raw !== "string" || !raw) return;
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return; // corrupt value reads as empty, never throws
    }
    if (!Array.isArray(parsed)) return;
    for (const id of parsed) if (typeof id === "string" && known.has(id)) read.add(id);
  };

  const save = () => {
    if (!store) return;
    const ordered = ids.filter((id) => read.has(id));
    try {
      store.set(key, JSON.stringify(ordered));
    } catch {
      // storage failure (private mode, quota) must not break reading
    }
  };

  load();
  if (store) {
    let flag = null;
    try {
      flag = store.get(enabledKey);
    } catch {
      flag = null;
    }
    enabled = flag !== "0";
  }

  // An id outside the notebook order is not a page this tracker can mark;
  // turns that land on supplemental render pages stay out of the stored set.
  const isKnown = (id) => typeof id === "string" && known.has(id);

  return {
    key,
    enabledKey,
    dwellMs,
    order: [...ids],
    isKnown,
    isEnabled: () => enabled,
    setEnabled(on) {
      enabled = !!on;
      if (store) {
        try {
          store.set(enabledKey, enabled ? "1" : "0");
        } catch {
          // storage failure must not break reading
        }
      }
      return enabled;
    },
    isRead: (id) => isKnown(id) && read.has(id),
    markRead(id) {
      if (!enabled || !isKnown(id) || read.has(id)) return false;
      read.add(id);
      save();
      return true;
    },
    readCount: () => read.size,
    // In notebook order, so a stored set always reads back deterministically.
    readIds: () => ids.filter((id) => read.has(id)),
    // Stop at the ends: the last page stays the last page, never wraps.
    nextId(id) {
      const i = indexOf.get(id);
      if (i === undefined || i + 1 >= ids.length) return null;
      return ids[i + 1];
    },
    prevId(id) {
      const i = indexOf.get(id);
      if (i === undefined || i - 1 < 0) return null;
      return ids[i - 1];
    },
    // Held at readable size for at least the dwell: counts as read.
    noteHeld(id, heldMs) {
      if (typeof heldMs !== "number" || heldMs < dwellMs) return false;
      return this.markRead(id);
    },
    // A page turned away from counts as read.
    noteTurned(fromId) {
      return this.markRead(fromId);
    },
  };
}

/**
 * Draft-bearing pages: a page whose lines include one from a non-current
 * version of its piece. Lines carry `ver`, the stack position of their
 * version with 0 the current (newest) version, so ver > 0 is a draft line.
 * `lines` is the reader's LN (each with `pi`, the index into `pages`);
 * `pages` is the reader's P. Returns a Set of page ids.
 */
export function computeDraftPages(lines, pages) {
  const out = new Set();
  if (!Array.isArray(lines) || !Array.isArray(pages)) return out;
  for (const line of lines) {
    if (!line || typeof line.ver !== "number" || line.ver <= 0) continue;
    const page = pages[line.pi];
    if (page && typeof page.id === "string") out.add(page.id);
  }
  return out;
}
