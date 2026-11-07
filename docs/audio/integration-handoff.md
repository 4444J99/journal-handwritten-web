# T09 integration handoff

Status: **staged; no live reader or studio wiring**. This draft prepares a private pilot for
[#23](https://github.com/4444J99/journal-handwritten-web/issues/23),
[#24](https://github.com/4444J99/journal-handwritten-web/issues/24), and
[#35](https://github.com/4444J99/journal-handwritten-web/issues/35). A real-recording listening
decision must precede one browser playback integration. No creative captions, performed lines,
audio palette or public permissions are chosen by this handoff.

## Refreshed baseline and existing owners

Main was read through the GitHub connector at
`038d01fb1862f2e569d231b5b3c4c3a4eb1aecda`, tree
`61618a204611a0e5dafb5485c6d99007ef679554`. An independent local copy was created in a new
directory from available Git objects, checked out on `t09/audio-pilot-2026-11-05`, and verified
against all **769** remotely listed tracked blobs. It is a shallow repository; no claim of complete
historical recovery is made. The supplying T05 checkout was clean and was not modified.

The three primary issues were open with zero comments at intake. Searches for audio/voice PRs
located the source-import PR [#103](https://github.com/4444J99/journal-handwritten-web/pull/103),
merged at `04168b1f68bc4579fae245f8411b0b337d064369`. The four supplied audio source documents
match the corresponding repository files byte for byte. No audio recording was found among the
769 baseline blobs, direct supplied files, or the two supplied ZIP inventories. That is the scope
of the absence finding; it does not assert that no recording exists on another device or service.

Reader verifier PR [#97](https://github.com/4444J99/journal-handwritten-web/pull/97) is merged.
Its two later cleanup/handshake findings were followed by merged
[#118](https://github.com/4444J99/journal-handwritten-web/pull/118) at `d74df372`; the current
`tools/cdp_client.mjs` waits for browser termination. T09 reuses the existing repository checks
and does not revise that verifier. T04's work remains separately owned; no completed T02/T04
agreement was found in the remote branch/PR searches. A search miss is a retrieval limit, not
proof that no work exists.

Posting PR [#101](https://github.com/4444J99/journal-handwritten-web/pull/101) is merged with
head `15cad30cb923161716be51b2d075a6b98062cad4`. Its remaining hardening findings are tracked in
[#123](https://github.com/4444J99/journal-handwritten-web/issues/123), still open at intake.
T09 neither executes posting nor claims those findings resolved. T03 draft
[#119](https://github.com/4444J99/journal-handwritten-web/pull/119), head
`8d16284ba8b80f18398d08b8de931d8812f30429`, remains a separately tested stack on
`post-poem-gates`. Its proposed clearance interface is a useful handoff, not a merged release
approval. T05 draft [#126](https://github.com/4444J99/journal-handwritten-web/pull/126), head
`c6930bb48f07fe81e23b3126aeaf5947fb4406e1`, documents the same existing identities and the need
for T02 agreement. Neither draft is merged or copied into this branch.

## T02 · immutable source and transcript binding

The following mapping is observed in the current data, independently of image layout:

| Field | Existing source | Consumption rule |
|---|---|---|
| `piece_id` | `site/data/j.json` → `pieces[].id` | Preserve the existing ID; n/100 numbering is not identity |
| `version_id` | The same piece's `V[].id` and `P` membership | Select an exact version; do not infer it by stack or review-array position |
| `line_ids` | `studio/data/review.json` line IDs within matching page/block membership | Preserve order and exact membership; display boxes never anchor audio |
| `source_revision` | Full Git commit and relevant input hashes | A local fixture may cite a fixture source instead; it must not borrow an author identity |
| `transcript_sha256` | Exact effective text snapshot with its review export | Original reading, correction and uncertainty remain distinguishable |
| `pronunciation_revision` | Reviewed lexicon plus author overrides | Unknown/changed words re-enter review; do not guess or use stale pronunciation |

T09 proposes a future audio binding containing those fields, a manifest hash, bank/engine revision,
segment lineage and output hash. T02 should accept or revise the exact schema before real reader
consumption. Current fixtures deliberately do not voice an unverified poem. Uploaded versions
that are not in the canonical mapping remain ineligible. A mismatch invalidates current playback
and emits a review diagnostic; preserve the prior recording/render as historical evidence.

An optional word anchor should be an exact text selector plus explicit code-point offsets when
needed, relative to the pinned line. Do not derive it from a screen coordinate or a phoneme's
playback time. Audio timing can refer to that selector after alignment; it cannot create source
identity by itself.

## T04 · one playback adapter after listening acceptance

The local controller is an implementation candidate for the lifecycle below. Its test receipt
covers the private harness only. It does not change `site/index.html`, add a keyboard shortcut,
or introduce a second focus/navigation state machine.

| Event from the reader | Required audio behavior |
|---|---|
| Initial load/reload | Off; no automatic resume from saved preference; no bank download before user action |
| Explicit Start in revealed controls | Resume/create the audio context within the user gesture, validate the selected rendered asset, then play exactly that asset |
| Explicit Stop | Invalidate pending decode/start operations and stop/disconnect the active source |
| Focus exits, piece/version changes, arrangement interruption | Invalidate the old context and stop; the new context must not inherit authorization to play |
| Tab hidden, pagehide/navigation or platform interruption | Stop/invalidate; coming back requires a fresh Start |
| Decode/fetch failure, stale binding, missing word/unit | Visible private diagnostic; no alternative voice, guessed token or autoplay recovery |
| End of sample | Return to a stopped/ready state; no loop unless a later selected design explicitly requires it |
| Component destroyed | Remove event listeners, stop sources and release audio resources |

Reader integration must consume T04's accepted exact focus/version context and shared hidden
controls. Do not attach competing keyboard handlers or alter progress/completion semantics.
Author caption choice, if any, uses exact author text. The journal title stays `versforms` and its
font identity `ajp-scribbles`; no other project's music identity is carried into a presentation.

Browser state behavior is informed by the [Web Audio 1.1 working draft](https://www.w3.org/TR/webaudio/)
and [Audio Session working draft](https://www.w3.org/TR/audio-session/), checked 2026-11-05.
These are evolving specifications, not proof of behavior on a particular phone. WebKit's
[silent-switch issue](https://bugs.webkit.org/show_bug.cgi?id=237322) records an iOS 17
`playback` session option. This draft does not set that option or run a silent-media workaround.
D14 and physical-device verification remain open.

Before accepting the reader adapter, test the integrated accepted reader revision on the author's
actual iPhone with silent switch on/off, built-in speaker and earbuds, explicit start/stop, a call
or competing audio interruption, screen lock, tab/app switch, version/focus changes, and rapid
start/stop during decode. Record OS/browser version, exact outputs and observed outcomes.
Desktop Chromium emulation cannot satisfy those checks. Test decoded memory and canvas
frame behavior after adding the real selected audio; the historical ~40 MB budget is a proposal.

## T03 · raw privacy and rendered release eligibility

The private pilot is not an additional posting route. After a real listening selection, supply
T03 with the rendered file hash/size, exact source/version/line set, input manifest hash,
pronunciation revision, processing/bank/engine revisions, author's sound decision, rights
decision and physical-device receipt. The author's clearance must identify the exact rendered
output. Listening preferences, a QC pass, a `series` label and a successful renderer do not grant
publication permission.

Extend the proposed
[`versforms.release-clearance.v1` contract](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/docs/releases/release-clearance-contract.md)
through its owner. List every shipped audio file in the exposure manifest. Public data must not
include private take paths, recordings, alignment drafts, rejected units, unknown-word queues,
withheld version identifiers, or full private receipts. A rendered file can still expose the words
of a withheld poem even if its filename is opaque. Recheck audible content and exact source
membership. Changing the text, selected take, palette, processing parameters or output bytes
requires a new matching clearance.

Keep three questions separate: may the author use this voice in other work; may a raw bank/master
be shared; may this exact rendered poem be published now? The pilot answers none by default.
Raw masters remain outside `site/`, `studio/` and the listening server's routes. No real bank is
packaged or pinned to a `v1.0.0` release by T09.

## Studio integrator · local workflow before a shared tab

The standalone workbench is under `audio_pilot/`; the renderer and packet builder are under
`audio_build/`. It uses local immutable input/output files and exports feedback/progress as JSON.
It creates no new service, account, database collection or deployment. The studio index remains
under its existing integrator. No private server is exposed on a LAN for phone testing.

After author listening acceptance, the integrator can place one Sound/Voice entry in the shared
studio, preserving its existing persistence adapter. Agree a collection/export contract for
pronunciations and listening revisions before adding writes. A useful proposed record includes
an immutable record ID, session/render/manifest hashes, exact source binding, keep/reject/defer,
author note, reviewer/date, devices used and a separate release-clearance reference. A feedback
export is not a write to that collection and is not an author signature.

The pronunciation queue should retain the token, original reading, proposed pronunciation,
authority, source version and review status. Explicitly silent and illegible are distinct states;
neither is an unknown word silently dropped. Export and restore the chosen record before any
integration claim. Performed material and full-bank controls remain absent until their gate.

## Return conditions

All three primary issues stay open. The next owner action is to choose the small set of acquisition
inputs and provide the combined pilot recordings; the next engineering action is to validate,
label and render those exact inputs. The author's listening choice comes next. Full acquisition,
reader/studio wiring, public release and any account action follow separately. The inaccessible
shared context packet is not a basis for any of these actions.
