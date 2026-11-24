// Pure derivation for the Release tab's Tracker sub-view (journal-handwritten-web #62).
//
// The tracker shows the whole n/100 series at a glance: one row per slot,
// derived from the same live state the Calendar sub-view already reads —
// never from a hand-kept file (the packet CSV went stale exactly because
// nothing read it). No DOM, no studio database access: the studio passes
// shaped inputs in and renders the rows. Tested by tests/test_release_tracker.mjs.
//
// Slot model (from the #62 plan, hardened against live source at main b2b92b7c):
// - 100 rows, one per planning slot. Slot i+1 holds the i-th Series piece in
//   queue order (seriesList order); slots past the end of the queue are blank.
// - Numbering follows numberingMode(): 'fixed' assigns i+1; 'as-posted' uses
//   the piece's recorded number once posted and shows nothing before that;
//   undecided mode behaves like as-posted (same as the Calendar).
// - Status mirrors the Calendar gates: 'posted' when a public exposure exists,
//   'ready' when verified + GRUW batch filed/registered + all PREP complete,
//   otherwise 'in queue'. An empty slot is 'unassigned'.
// - A piece whose pool is not 'series' can never take a slot: seriesList()
//   already filters to Series, and trackerRows() skips non-Series entries
//   defensively, so a Reserve piece can never be given a slot number here
//   (the #65 Reserve hard stop, enforced at the public-site builder too).
// - Post date is the public exposure's date when posted, else the projected
//   week date (First-post date + 7 days per slot); blank when no start date.
// - Unsorted pieces (no pool yet) are not slot rows: unsortedPieces() lists
//   them separately so the author can see and sort them.

export const TRACKER_SLOTS = 100;
export const TRACKER_CSV_HEADER = 'planning_slot,assigned_number,piece_id,status,confirmed_date,public_url';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function isPublicAppearance(e) {
  return e && (e.type === 'social' || (e.type === 'site' && e.target !== 'staging'));
}

function isValidPostUrl(u) {
  return typeof u === 'string' && /^https?:\/\/[^\s]+$/.test(u.trim());
}

// 'YYYY-MM-DD' + n days -> 'YYYY-MM-DD'. UTC math so the date never shifts with the viewer's zone.
export function addDaysISO(start, days) {
  if (typeof start !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(start)) return '';
  const d = new Date(start + 'T00:00:00Z');
  if (isNaN(d)) return '';
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

// 'YYYY-MM-DD' -> 'Jan 5', with a two-digit year when it is not this year (same shape as shortDate()).
export function shortDateISO(iso) {
  if (!iso) return '';
  const d = new Date(iso + 'T12:00:00Z');
  if (isNaN(d)) return '';
  const label = `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
  return d.getUTCFullYear() !== new Date().getUTCFullYear() ? `${label} ’${String(d.getUTCFullYear()).slice(2)}` : label;
}

function csvField(v) {
  const s = v == null ? '' : String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// series: Series pieces in queue order, each {key, title, pool, verified, num,
//   exposures, prepDone, prepTotal, batchStatus}.
//   pool must be 'series' for the piece to take a slot; anything else is skipped.
// mode: 'fixed' | 'as-posted' | '' (from numberingMode()).
// start: First-post date 'YYYY-MM-DD' or '' (from rconfig/settings).
// Returns exactly TRACKER_SLOTS rows:
//   {slot, number, pieceId, title, status, dateISO, dateLabel, url}
export function trackerRows({ series = [], mode = '', start = '' } = {}) {
  const queue = series.filter(p => p && p.pool === 'series');
  const rows = [];
  for (let i = 0; i < TRACKER_SLOTS; i++) {
    const p = queue[i];
    if (!p) {
      rows.push({ slot: i + 1, number: null, pieceId: '', title: '', status: 'unassigned', dateISO: '', dateLabel: '', url: '' });
      continue;
    }
    const posted = (p.exposures || []).find(isPublicAppearance);
    const ready = !!p.verified && (p.batchStatus === 'filed' || p.batchStatus === 'registered')
      && typeof p.prepDone === 'number' && typeof p.prepTotal === 'number' && p.prepTotal > 0 && p.prepDone === p.prepTotal;
    const number = mode === 'fixed' ? i + 1 : (typeof p.num === 'number' ? p.num : null);
    const projected = addDaysISO(start, 7 * i);
    rows.push({
      slot: i + 1,
      number,
      pieceId: p.key || '',
      title: p.title || '',
      status: posted ? 'posted' : ready ? 'ready' : 'in queue',
      dateISO: posted ? (posted.date || '') : projected,
      dateLabel: posted ? shortDateISO(posted.date || '') || (posted.date ? 'posted' : '') : shortDateISO(projected),
      url: posted && isValidPostUrl(posted.url) ? posted.url.trim() : '',
    });
  }
  return rows;
}

// CSV in the packet schema (release/packets/*/release-tracker-100-slots.csv):
// planning_slot,assigned_number,piece_id,status,confirmed_date,public_url.
// Generated from the same derived rows the view renders, so the export can
// regenerate the packet file instead of leaving a second tracker to go stale.
export function trackerCsv(rows) {
  const lines = [TRACKER_CSV_HEADER];
  for (const r of rows || []) {
    lines.push([r.slot, r.number == null ? '' : r.number, r.pieceId, r.status, r.dateISO, r.url].map(csvField).join(','));
  }
  // CRLF, matching the packet CSVs in release/packets/ byte for byte, so the
  // export can regenerate the packet file.
  return lines.join('\r\n') + '\r\n';
}

// Pieces with no pool yet, for the supplementary list under the 100 rows:
// [{key, title}] -> [{key, title, status: 'unsorted'}]. Reserve/Archive pieces
// are not unsorted — they have a pool, so they never appear here.
export function unsortedPieces(pieces = []) {
  return pieces.filter(p => p && !p.pool).map(p => ({ key: p.key || '', title: p.title || '', status: 'unsorted' }));
}
