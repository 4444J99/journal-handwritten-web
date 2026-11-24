// Lane model for the Release tab's weekly calendar (JHW #41).
//
// The Oct 31 relaunch design is "weekly poem with daily 'lanes' (poem,
// handwriting/process, translation, audio, animation, reflection), opened
// only as work exists". A release record carries the lanes in a `lanes` map:
// one entry per lane kind, each `{ state: 'absent' | 'ready' | 'posted',
// url?, date? }`. Records written before lanes existed have no `lanes` key
// and read as all-absent: no migration, no backfill.
//
// One deliberate asymmetry, because the poem lane already has a source of
// truth: the poem row's gates (verified / GRUW filed-or-registered / prep
// complete) and its posted exposure ARE the poem lane's state, so the studio
// derives the poem lane from those and never persists a poem entry. This
// module still normalises a stored `poem` entry if one is ever written
// (tolerated, not rendered from), but `laneEntries` / `lanesReadyCount`
// cover only the five filler lanes — the `lanes n/5 ready` chip counts
// filler lanes with work present, and it never gates the poem's readiness.
//
// Pure module: no DOM, no imports, so the node suites can test it directly
// and the studio page loads it with a dynamic import in boot().
export const LANE_KINDS = [
  ['poem', 'Poem'],
  ['process', 'Handwriting / process'],
  ['translation', 'Translation'],
  ['audio', 'Audio'],
  ['animation', 'Animation'],
  ['reflection', 'Reflection'],
];

// The five non-poem lanes: the week's filler work, opened only as it exists.
export const FILLER_LANES = LANE_KINDS.slice(1);

export const LANE_STATES = ['absent', 'ready', 'posted'];

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

// Normalise a release record's lanes map into a complete six-kind map.
// Anything missing, malformed, or unknown reads as absent; url/date survive
// only on a lane that actually has work (ready/posted), so an absent lane
// can never carry a stale link or date.
export function normalizeLanes(record) {
  const out = {};
  for (const [kind] of LANE_KINDS) out[kind] = { state: 'absent' };
  const raw = record && typeof record === 'object' && !Array.isArray(record) ? record.lanes : null;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return out;
  for (const [kind] of LANE_KINDS) {
    const e = raw[kind];
    if (!e || typeof e !== 'object' || Array.isArray(e)) continue;
    if (!LANE_STATES.includes(e.state)) continue;
    const entry = { state: e.state };
    if (e.state !== 'absent') {
      if (typeof e.url === 'string' && e.url.trim()) entry.url = e.url.trim();
      if (typeof e.date === 'string' && DATE_RE.test(e.date)) entry.date = e.date;
    }
    out[kind] = entry;
  }
  return out;
}

// The week's filler lanes as a view model: one entry per kind, in design
// order, each with its label and normalised state. The calendar renders one
// row per entry — a lane row when work exists, a quiet "no work yet" line
// when the lane is absent.
export function laneEntries(record) {
  const lanes = normalizeLanes(record);
  return FILLER_LANES.map(([kind, label]) => ({ kind, label, ...lanes[kind] }));
}

// Filler lanes with work present (ready or posted), out of the five.
export function lanesReadyCount(record) {
  return laneEntries(record).filter(e => e.state !== 'absent').length;
}

// One week's lane view model, for the calendar and its tests.
export function weekLanes(record) {
  const lanes = laneEntries(record);
  return { lanes, readyCount: lanes.filter(e => e.state !== 'absent').length, total: FILLER_LANES.length };
}
