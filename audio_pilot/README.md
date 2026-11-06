# Private T09 listening workbench

This local pilot is separate from the journal reader and studio. It never records microphone input, uploads files, releases audio, or decides artistic settings. Fixture audio tests the pipeline; it does not establish an author voice or an accepted sound direction.

Generate a packet and listening output with `audio_build/render.py` (see `audio_build/INTERFACE.md`), then run from the repository root:

```sh
python3 audio_pilot/serve.py --renders /absolute/listening --packet /absolute/packet --port 8765
```

Open `http://127.0.0.1:8765/`. Click **Load receipt and prompts from local server**, choose a sample, click **Load selected sample**, then **Start**. Opening the page loads no receipt, prompt data, or audio. Loading a sample checks its receipt hash and decodes it without playing it. Stop, page hiding, navigation, context interruption, sample changes, and packet reload invalidate outstanding playback operations. Returning to the page never resumes audio. Only one sample plays, once, at a time. Listening gain starts at 25%; that is a workbench control, not a rendering or artistic default.

The server binds only `127.0.0.1`. It accepts only that exact host and port. Its allowlist contains the five workbench files, the configured receipt and prompt JSON, and receipt-listed rendered WAVs under `samples/`. It denies directories, raw recordings, paths with encodings or traversal, symlinks, and samples whose SHA-256 changed. No write or upload route exists. Do not replace this server with a broad directory server over a recording folder.

Both the server and the UI require the receipt’s session ID and lowercase SHA-256 manifest identity. The receipt is returned unchanged, including additional producer provenance fields. Keeping raw filesystem paths out of receipt metadata is the producer’s responsibility; this workbench validates identities and routes, and does not redact the receipt or infer whether a listed waveform was properly rendered. Use the engine’s listening output as `--renders`, never an improvised raw-recording receipt.

For direct-file use, open `audio_pilot/index.html`, select the receipt and prompts through the file inputs, then select the matching rendered WAV files. Only receipt-listed files that pass SHA-256 verification can play. If the browser does not offer Web Crypto on a file URL, use the loopback server. Neither mode persists data in browser storage. Export progress and notes before closing.

The prompter supports previous/next, rehearsal, pause, repeat requests, and external take references. It does not operate the external recorder. Required unresolved author decisions are visible and disable external-take logging for that prompt; rehearsal remains available. Its resolution check matches the engine: an entry needs a nonempty `choice`, `author` and `source` (or the decision sheet’s `value`, `authority` and `source_ref` aliases). Changing data does not invent or authorize decisions. Confirm decisions in `docs/audio/author-decisions.md` before acquisition.

Listening feedback exports include sample and manifest hashes, fixture status, gain and user-entered notes whose authorship is unverified. They explicitly deny release, acquisition and sound-direction approval. Exported feedback is an input to a later author listening decision. The prompter export records references and progress, never audio or creative captions. Each progress entry retains its original packet ID, prompt-file hash, prompt snapshot and decision snapshot; loading another packet does not relabel or discard previous entries.

## Integration surface and verification

`playback.js` exposes `globalThis.T09Playback`. The workbench exposes its instance as `window.t09Player` for QA. Public methods are `load(sample, source)`, `start()`, `stop(reason)`, `invalidate(reason)`, `setVolume(value)`, `snapshot()` and `destroy()`. Call `invalidate` on any source ID, version, entry, arrangement or release-context change when the later T04 integration is authorized. This pilot does not wire reader or studio events. Its startup and load cancellation use generation tokens; an interrupted fetch, decode or resume cannot restart sound.

```sh
node --test tests/test_audio_playback.mjs
python3 -m unittest discover -s tests -p 'test_audio_harness.py' -v
```

Automated controller tests use fake audio contexts, not a physical output device. Real-browser QA is separate. Physical iPhone silent-switch, lock, calls, speaker and earbud behavior remains untested. No `AudioSession` override, keepalive or autoplay workaround is applied; the author choice and device matrix remain open. Raw-bank privacy and released rendered audio are separate decisions.
