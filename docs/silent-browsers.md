# Silent browsers

No tool or test in this repository may produce audible sound on the host. The mute sits at the source:

- `tools/silent_browser.cjs` is the one launch helper. `silentLaunch(engine, options)` launches a Playwright browser with `--mute-audio` merged into Chromium's own arguments, and gives every context (`newContext`, and `newPage`, which makes its own) `tools/silent-init.js`. `silentChromeArgs([...])` merges the same flag into the arguments of a Chrome a tool spawns itself and drives over CDP.
- `tools/silent-init.js` is engine-agnostic, so it is the mute for WebKit and Firefox, which have no flag. It pins audio and video elements to native `muted = true` and `volume = 0` (the page still reads back what it set), routes every connection to a realtime `AudioContext` destination through a gain-0 sink, leaves `OfflineAudioContext` on its real destination, and speaks `speechSynthesis` utterances at volume 0. An element routed through `createMediaElementSource` is released from the pin (a muted element would feed silence to the analysers) and silenced in the graph instead.
- `tools/silent_launch_lint.py` fails on any Playwright launch or headless Chrome spawn that skips the helper. `tools/check.py` runs it, so it is part of the repository gate, and `tests/test_silent_launch_lint.py` proves it sees every launch style used here.
- `tests/test_silent_browser.mjs` proves the helper contract and, where Playwright is installed, the page behaviour with silent fixtures (set `SILENT_BROWSER_REQUIRE_PAGE=1` to make a missing Playwright a failure).
