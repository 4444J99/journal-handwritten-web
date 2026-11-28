---
title: "Notebook Chat 01 — Variorum 7-Layer Coordinates, C/S Delineation, Schema & Live Test"
source_notebook: "versforms"
export_date: "2026-11-22"
branch: "docs/notebook-chat-01-variorum-coordinates"
completeness: "partial-excerpt"
completeness_note: "Preserves all retrieved turns and sections from the notebook session verbatim. Sections clipped by notebook retrieval (e.g., initial social release rollout section between 7-layer intro and platform architecture, and the follow-up user turn that locked C/S) are explicitly marked and can be topped up from a full export."
affected_repos:
  - 4444J99/journal-handwritten-web
  - 4444J99/versforms
  - 4444J99/linguistic-atomization-framework
privacy: "private-source-of-record"
---

# Notebook Chat 01 — Variorum 7-Layer Coordinates, C/S Delineation, Schema & Live Test

> **Provenance:** Externalized from the `versforms` research notebook on `2026-11-22`.  
> **Completeness:** `partial-excerpt` (see frontmatter). Superseding note: `A/I` sigla discussed in Turn 1 were retired later in this session and locked permanently to **`C` (Codex)** and **`S` (Supplementum)**.

---

## Turn 1 — User

So talking this out, we have a series of handwritten poems. There's a certain number of them. You'll see this in the There's two repositories that deal with this that deal with this this project that I'm talking about. One is called Verse Forms and the other is called Journal Handwritten Web. Now, there's a sequence of poems. They're the original sequence, and they're original in the sense that I started the book and I wrote through the book, and now that that journal's gone, right? It doesn't exist anymore. This is over 10 years ago. Now I'm returning for them and reviewing them, revising them, and releasing them on the platforms that we're building, but also on social. So I'm trying to figure out what to do with them and how to release them. My instinct right now is to, on Instagram at least, I don't know what else, one of the platforms. And so for all of my non my unknowns, this is part of what you'll be helping me decide. On socials, release put on as posts all of the originals one at a time. And then, round two, pair them with their revision, you know, then do a second round of posts pairing them with their revisions. Okay? However, part of the process is there's a certain number of poems that are in the original amount version. Now, that'll And the idea is that we're going to There's going to be that original number. I forget what it is. It might be 60 something. It might be 50 something. But the idea is to fill out the number to 100 and number all of them, right? So we need to develop a sort of Dewey Decimal System for the the different poems, right? But the complication being that there's the original set, okay? The original set are getting revisions upon revisions, right? This is part of the project. And then there's the filler-in set for the to reach the 100, which will also get revisions. So you should put And then it's part of the project is that they'll get revisions forever. So maybe I'll return to it again in 10 years. And so maybe it's important to explain at this point that also they're going to get in-text citations and notes and footnotes and also, you know, so basically we need a system that tracks every line, letter, character, etc., right? Like every part of the word down to every character. So that's kind of what we're trying to develop right now is how to reference every from the collection level to the piece level to the paragraph level to the sentence level to the line level to each part of each word level to each character level and also the social release of it all as I'm doing this.

## Turn 1 — Gemini

Building a perpetual variorum that tracks 100 poems across decades—from collection down to individual characters—while rolling them out publicly requires treating **citation coordinates as both your database schema and your aesthetic hook**.

---

### 1. The 7-Layer Coordinate System ("Variorum Dewey Decimal")

Because poetry has **enjambment** (sentences crossing line breaks, or multiple sentences inside a single line), a strict single hierarchy (Paragraph → Sentence → Line) will break as soon as a sentence spans two lines.

The cleanest solution is a **two-part Canonical Locus string**: a **Macro-Address** (which identifies the collection, the 1–100 slot, whether it is an original or filler-in poem, and its revision number) separated by a colon from a **Micro-Address** (which tracks the structural, syntactic, and character coordinates).

```text
[Collection].[Slot]-[Genesis].[Stratum] : P[n].S[n].L[n].W[n].[Part].C[n]
Example: JHW.042-A28.r1 : P02.S03.L07.W04.m2.C03
```

| Level | Segment | Code Example | What It Tracks |
| :--- | :--- | :--- | :--- |
| **1. Collection** | Corpus | `JHW` or `VF` | Repository or project namespace (`journal-handwritten-web` / `verse-forms`) |
| **2. Piece** | Slot + Genesis + Stratum | `042-A28.r1` | Canonical slot (`042` of `100`), origin (`A28` = 28th original), revision (`r1`) |
| **3. Paragraph** | Stanza / Block | `P02` | Visual stanza, verse paragraph, or manuscript block |
| **4. Sentence** | Syntactic Unit | `S03` | Grammatical sentence across line breaks (handles enjambment) |
| **5. Line** | Verse Line | `L07` | Physical/typographical line number (either stanza-relative or poem-total) |
| **6. Word & Part** | Lexeme + Sub-word | `W04.m2` or `W04.s2` | 4th word on the line; `.m` = morpheme (prefix/root/suffix), `.s` = syllable |
| **7. Character** | Grapheme | `C03` or `C03-06` | 3rd letter/glyph inside that word or sub-word span |

**How the Piece Identifier (`042-A28.r1`) solves the "Original vs. Filler-to-100" problem:**

* **Canonical Slot (`001`–`100`):** Every poem gets a permanent two- or three-digit slot in the final 100-poem architecture.
* **Genesis Code (`A` vs. `B`/`I` — later locked to `C`/`S`):**
  * `A[nn]` (Autograph / Original): Preserves the exact sequence from the lost physical journal (e.g., `A01` through `A62`). Even if you weave new poems *between* the originals, `042-A28` always remembers that poem `#042` in the final 100 was originally the 28th poem in the notebook.
  * `I[nn]` (Interpolated / Supplement): Marks the ~35–45 "filler-in" poems written to complete the 100 (e.g., `043-I14` is the 43rd poem in the canon, and the 14th supplemental piece).
* **Infinite Revision Strata (`r0`, `r1`, `r2`... or `r1.0`, `r2.0`):**
  * `r0` is always the diplomatic base layer (for original poems, the 10-year-old handwritten scan and literal verbatim transcription, including cross-outs and misspellings; for interpolated poems, their initial first draft).
  * `r1`, `r2`, `r3` track sequential revisions. If you want to separate *current* iterative edits from a return 10 years from now, use `r[Epoch].[Edit]`—where `r0.0` is the 2016 notebook, `r1.0`, `r1.1`, `r1.2` are your 2026 revisions, and `r2.0` is your 2036 return.

**Why `.m` (Morpheme) and `.s` (Syllable) matter at Level 6:**

* If you want to annotate *parts of a word*, you are usually doing one of two things: **etymological/semantic analysis** (splitting *un-forget-table* into prefix `m1`, root `m2`, suffix `m3`) or **prosodic/metrical scansion** for `verse-forms` (splitting *un-for-get-ta-ble* into syllables `s1` through `s5`). Supporting `.m[n]` and `.s[n]` lets your footnotes target either grammar or meter down to the exact character (`C[n]`).

**Keeping footnotes intact across infinite revisions:**

* Never hardcode a footnote to a raw character offset that shifts when you edit a line. Instead, each footnote anchors to the **immutable coordinate of the stratum it comments on** (e.g., a note attached to `042-A28.r0:P1.S1.L2.W5.C1` stays permanently bound to `r0`, while a comparative note links `r0:L2.W5 → r1:L2.W4`).

`[... retrieved excerpt boundary: Section 2 (Social Release Rollout) omitted in retrieved context ...]`

### 3. Platform Architecture: Where Each Layer Lives

Instagram handles visual contrast well, but it flattens hypertext and footnotes. Splitting the release across three complementary surfaces keeps every layer of your coordinate system functional:

* **The Canonical Hub (`journal-handwritten-web` & `verse-forms`):** Houses the full interactive variorum: timeline slider between `r0`, `r1`, `r2`..., toggleable coordinate overlays (stanza, sentence, line, morpheme, character), and bidirectional footnotes.
* **Visual Feed (Instagram + Threads / Bluesky):**
  * **Instagram:** Carousels showing the physical-to-digital artifact transformation and zoomed-in manuscript diagnostics.
  * **Threads / Bluesky:** Micro-citations. Post a single excised line or a character-level footnote (`019-A12.r1 : L03.W05` — *"Changed 'stone' to 'slates' after 11 years; see note 4"*) linking directly to that coordinate anchor on the web app.
* **Deep Apparatus & Serialization (Substack or Ghost + Are.na):**
  * **Substack / Ghost:** Weekly or biweekly "Variorum Dispatches" grouping 3–5 poems with their full clickable footnotes, commentary on the lost journal, and audio readings.
  * **Are.na:** Mirror the 100-poem index as an open research channel where scans, revision diffs, and footnote blocks cross-link visually.

---

`[... retrieved excerpt boundary: Follow-up turn transitioning to C (Codex) / S (Supplementum) sigla omitted in retrieved context ...]`

## Refined Specification (C/S Sigla + SQLite/D1 + JSON AST + Live Test)

### 2. The 7-Layer Coordinate Grammar

To address every unit from the collection down to the character—without breaking when a sentence enjambs across multiple lines—the coordinate string uses a **Macro-Address** (Levels 1–2) and a **Micro-Address** (Levels 3–7):

```text
[Collection].[Slot]-[Genesis].[Stratum] : P[nn].S[nn].L[nn].W[nn].[Subword].C[nn]
```

* **Level 1 (Collection):** `JHW` (`journal-handwritten-web`) or `VF` (`verse-forms`)
* **Level 2 (Piece & Stratum):** `001-C01.r0` (Slot 001, Codex poem 01, Stratum `r0`). Sub-layers of ink on the original page use `r0.i1` (primary ink), `r0.i2` (marginal pencil/second ink).
* **Level 3 (Paragraph / Stanza):** `P01` (1-indexed stanza or prose-poem block)
* **Level 4 (Sentence):** `S01` (1-indexed syntactic unit across the poem, independent of line breaks)
* **Level 5 (Line):** `L01` (1-indexed physical verse line across the poem)
* **Level 6 (Word & Sub-word):** `W04` (4th word on `L01`), with optional sub-word selectors:
  * `.m1`, `.m2`, `.m3` = **Morpheme** (prefix, root, suffix—for semantic/etymological shifts)
  * `.s1`, `.s2`, `.s3` = **Syllable** (for metrical/prosodic scansion in `verse-forms`)
* **Level 7 (Character / Grapheme):** `C01` (1-indexed character within the word, or `C01-03` for a character span; punctuation attached to a word is indexed as `.C[last]` or `.p1`)

---

### 3. Database (SQLite / D1) & JSON Schema

To keep the database fast and prevent every single letter from requiring manual entry, **SQLite/D1 stores the Piece, Stratum, Line, and Apparatus tables**, while the **Token AST (stored as a canonical JSON document per stratum and validated by your Python build script)** deterministically indexes every paragraph, sentence, word, morpheme/syllable, and character offset.

#### A. Relational Schema (Cloudflare D1 / SQLite)

```sql
-- 1. PIECES: Maps the 001-100 Century slots to C (Codex) or S (Supplementum)
CREATE TABLE pieces (
    piece_id TEXT PRIMARY KEY,          -- e.g., 'JHW.001-C01'
    collection_code TEXT NOT NULL,      -- 'JHW' or 'VF'
    century_slot INTEGER NOT NULL UNIQUE CHECK (century_slot BETWEEN 1 AND 100),
    genesis_class TEXT NOT NULL CHECK (genesis_class IN ('C', 'S')),
    genesis_seq INTEGER NOT NULL,       -- 1..64 for 'C', 1..36 for 'S'
    source_page TEXT,                   -- e.g., 'p001' (NULL for 'S' poems if digital-native)
    canonical_title TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (collection_code, genesis_class, genesis_seq)
);

-- 2. STRATA: Infinite revision layers per piece (r0, r0.i2, r1, r2...)
CREATE TABLE strata (
    stratum_id TEXT PRIMARY KEY,        -- e.g., 'JHW.001-C01.r0'
    piece_id TEXT NOT NULL REFERENCES pieces(piece_id),
    stratum_code TEXT NOT NULL,         -- 'r0', 'r0.i2', 'r1', 'r2'
    epoch_year INTEGER NOT NULL,        -- e.g., 2015, 2026, 2036
    parent_stratum_id TEXT REFERENCES strata(stratum_id),
    ast_json TEXT NOT NULL,             -- Full 7-layer deterministic JSON AST
    ast_sha256 TEXT NOT NULL,           -- Hash verified by check_parts.py
    is_published INTEGER DEFAULT 0,
    UNIQUE (piece_id, stratum_code)
);

-- 3. APPARATUS & FOOTNOTES: Anchored to exact 7-layer coordinate spans
CREATE TABLE apparatus_notes (
    note_id TEXT PRIMARY KEY,           -- e.g., 'note-001-C01-01'
    stratum_id TEXT NOT NULL REFERENCES strata(stratum_id),
    anchor_start TEXT NOT NULL,         -- e.g., 'P01.S02.L02.W04.m1.C01'
    anchor_end TEXT,                    -- Optional end coordinate for spans
    target_stratum_id TEXT REFERENCES strata(stratum_id),
    target_coord TEXT,                  -- Cross-reference to r1 or another poem (e.g., S01)
    note_type TEXT NOT NULL CHECK (note_type IN ('variant', 'gloss', 'erasure', 'prosody', 'citation')),
    body_markdown TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### B. The 7-Layer JSON AST (`ast_json` / `parts.json` structure)

```json
{
  "coordinate_root": "JHW.001-C01.r0",
  "meta": {
    "century_slot": 1,
    "genesis": { "class": "C", "sequence": 1, "manuscript_page": "p001" },
    "stratum": "r0",
    "ink_layers": ["i1_black_ballpoint", "i2_margin_graphite"]
  },
  "paragraphs": [
    {
      "id": "P01",
      "lines": [
        {
          "id": "L01",
          "ink_row": 1,
          "bbox": [112, 84, 890, 132],
          "words": [
            {
              "id": "W01",
              "sentence_id": "S01",
              "coord": "P01.S01.L01.W01",
              "text": "When",
              "morphemes": [{ "id": "m1", "text": "When", "char_span": [1, 4] }],
              "syllables": [{ "id": "s1", "text": "When", "stress": "/" }],
              "chars": [
                { "id": "C01", "g": "W" },
                { "id": "C02", "g": "h" },
                { "id": "C03", "g": "e" },
                { "id": "C04", "g": "n" }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

### 4. Live Test: Applying the System to a Poem Across Strata

#### Stratum `r0` (Original Notebook Base — `JHW.001-C01.r0`)

Suppose Stanza 1 (`P01`) on page `p001` reads:

* **L01:** `When is it for? Who is it`
* **L02:** `for—this unmasked iron`

Notice how **Sentence 2 (`S02`)** starts mid-way through `L01` (*"Who is it"*) and enjambs into `L02` (*"for—this unmasked iron"*). Because Sentence (`S`) and Line (`L`) are orthogonal coordinates in the micro-address, there is zero collision:

* `"When"` → `JHW.001-C01.r0 : P01.S01.L01.W01`
* `"Who"` (starts Sentence 2 on Line 1) → `JHW.001-C01.r0 : P01.S02.L01.W05`
* `"for"` (continues Sentence 2 on Line 2) → `JHW.001-C01.r0 : P01.S02.L02.W01`
* `"unmasked"` (broken into morphemes `m1` = *un*, `m2` = *mask*, `m3` = *ed*):
  * Full word: `JHW.001-C01.r0 : P01.S02.L02.W03`
  * Privative prefix *"un-"*: `JHW.001-C01.r0 : P01.S02.L02.W03.m1` (or characters `C01-02`)
  * Root *"mask"*: `JHW.001-C01.r0 : P01.S02.L02.W03.m2` (characters `C03-06`)
  * Single letter `"k"` in *unmasked*: `JHW.001-C01.r0 : P01.S02.L02.W03.m2.C06`

#### Stratum `r1` (10-Year Revision — `JHW.001-C01.r1`)

Ten years later, `L02` is revised from *"for—this unmasked iron"* to *"for: the half-masked wire"*:

* **Source (`r0`):** `JHW.001-C01.r0 : P01.S02.L02.W03.m1` (`"un"`)
* **Target (`r1`):** `JHW.001-C01.r1 : P01.S02.L02.W03.m1` (`"half-"`)
* **Footnote (`note-001-C01-04`):** *"Replaced privative prefix `m1` ('un') with compound qualifier ('half-') to reflect that the persona is never fully removed in the 2026 revision; punctuation at `L02.W01.p1` shifted from em-dash to colon."*
