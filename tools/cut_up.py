"""Cut-up version model (journal-handwritten-web #55).

A version record in site/data/j.json (and in the derived
studio/data/notes-versions.json) carries:

- ``method``: how the version was made — ``"original"`` (the default for
  every version that predates this module), ``"cut-up"`` (lines shuffled,
  struck, or kept from source lines into a new version), or ``"erasure"``
  (lines kept from a source version with the rest erased). Absent means
  ``"original"``: the backfill is a migration, not a requirement.
- ``src``: per-line provenance, present only on cut-up/erasure versions.
  A list parallel to the version's flattened line list (``P`` order):
  each entry is ``None`` (the line is the piece's own) or
  ``{"piece": <source piece id>, "line": <source line id>}`` naming the
  source line the words came from. A source line id is the stable
  ``"<page>-<block>-<line>"`` id the reader and review store use
  (e.g. ``"diary1-0-0"``).

Why this shape: page-level membership (``P``) says where a line sits, not
where its words came from. Without per-line provenance the fold-in view
and the Reserve-reuse warning cannot be computed at all, and the public
build cannot prove a cut-up version emits no Reserve text.

The Reserve rule lives in exactly one place — ``pool_of()`` in
tools/post_poem.py (the studio's exact values only; a value that merely
looks like Reserve is never read as Reserve). This module never
re-implements it: callers pass a ``pool_of`` callable (piece id -> pool
string) and this module only compares the returned exact value.
"""
METHODS = ("original", "cut-up", "erasure")

# Pools that must never reach public output or a Mark-posted record.
# All four non-Series pools, the same definition #65's shared-scan rule
# uses (post_poem.shared_scan refuses reserve, archive, unsorted, and
# unknown): a source piece with no release document ('unsorted') is not
# Series either, and letting it through would launder unclassified text
# into the public site through a cut-up, bypassing the release process.
WITHHELD_POOLS = ("reserve", "archive", "unsorted", "unknown")


def version_method(version):
    """The version's method; absent means 'original' (pre-#55 records)."""
    method = version.get("method", "original")
    if method not in METHODS:
        raise ValueError(f"unknown version method {method!r} on {version.get('id')}")
    return method


def line_id(page_id, block_index, line_index):
    """The stable line id the reader and review store use."""
    return f"{page_id}-{block_index}-{line_index}"


def flatten_lines(version, pages=None):
    """The version's lines in P order.

    With ``pages`` ({page id: page with B blocks of L lines}) this is the
    line list: [(page_id, block_index, line_index)]. Without pages only
    the (page_id, block_index) pairs are known, so the block pairs are
    returned instead; callers that need the line count pass pages.
    """
    out = []
    for page_id, blocks in version.get("P", []):
        for bi in blocks:
            if pages is None:
                out.append((page_id, bi))
            else:
                for li in range(len(pages[page_id]["B"][bi]["L"])):
                    out.append((page_id, bi, li))
    return out


def validate_version(version, pages=None):
    """Validate a version record's method/src shape; returns the method.

    Raises ValueError on: an unknown method; src on an 'original'
    version; a src entry that is neither None nor a {piece, line} object
    with string values; or (when pages are given) a src list whose length
    does not match the flattened line list.
    """
    method = version_method(version)
    src = version.get("src")
    if src is None:
        return method
    if method == "original":
        raise ValueError(
            f"version {version.get('id')!r} is 'original' but carries src provenance; "
            "only cut-up/erasure versions carry src")
    if not isinstance(src, list):
        raise ValueError(f"version {version.get('id')!r} src is not a list")
    for entry in src:
        if entry is None:
            continue
        if not isinstance(entry, dict) or set(entry) != {"piece", "line"}:
            raise ValueError(f"version {version.get('id')!r} bad src entry {entry!r}")
        if not isinstance(entry["piece"], str) or not isinstance(entry["line"], str):
            raise ValueError(f"version {version.get('id')!r} bad src entry {entry!r}")
    if pages is not None:
        lines = flatten_lines(version, pages)
        if len(src) != len(lines):
            raise ValueError(
                f"version {version.get('id')!r} src has {len(src)} entries for "
                f"{len(lines)} lines; src must parallel the flattened line list")
    return method


def reserve_sources(version, pool_of, pages=None):
    """Src entries whose source piece sits in a withheld pool.

    Returns a list of {"src": entry, "pool": pool} for each non-None src
    entry whose piece's pool (via the caller's exact-value ``pool_of``)
    is reserve, archive, unsorted, or unknown — every non-Series pool,
    the same definition #65's shared-scan rule uses. Own lines (None
    entries) and Series sources are never flagged. An 'original' version
    has no src and returns [].
    """
    validate_version(version, pages)
    bad = []
    for entry in version.get("src") or []:
        if entry is None:
            continue
        pool = pool_of(entry["piece"])
        if pool in WITHHELD_POOLS:
            bad.append({"src": entry, "pool": pool})
    return bad


def cut_up_record(piece_id, lines, src, *, at=None, method="cut-up", source_version=None):
    """The versions-collection document a Cut-tab save writes.

    ``lines`` is the kept line ids in order; ``src`` parallels it with
    one {piece, line} entry (or None for an own line) per line.
    The record carries a method ('cut-up' or 'erasure') so the Release
    warning and the public build can find it without loading j.json.
    ``source_version`` names the top version the cut was made from, so
    the reader can list an erasure's dropped lines; None when unknowable.
    """
    if len(lines) != len(src):
        raise ValueError("lines and src must parallel each other")
    record = {
        "pieceId": piece_id,
        "method": method,
        "lines": list(lines),
        "src": list(src),
        "at": at,
        "status": "new",
    }
    if source_version is not None:
        record["sourceVersion"] = source_version
    return record
