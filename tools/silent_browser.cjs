/* Launch every Playwright browser through here so no run can make a sound. Chromium gets --mute-audio merged into
 * the caller's arguments, and every context (newContext, and newPage, which makes its own) gets silent-init.js:
 * media elements pinned muted at volume 0 and a gain-0 sink in front of every realtime AudioContext destination.
 * The init script is engine-agnostic; Firefox also gets the media.volume_scale=0.0 pref (covers closed declarative shadow
 * roots). WebKit has no equivalent, so a closed declarative shadow root stays a documented limit there. */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

const INIT_SCRIPT_PATH = path.join(__dirname, 'silent-init.js');
const MUTE_ARGS = ['--mute-audio'];
const initScript = () => fs.readFileSync(INIT_SCRIPT_PATH, 'utf8');

const engineName = engine => (typeof engine.name === 'function' ? engine.name() : engine.name);

function silentArgs(name, args = []) {
  const merged = [...args];
  if (name === 'chromium') for (const flag of MUTE_ARGS) if (!merged.includes(flag)) merged.push(flag);
  return merged;
}

// Firefox has an engine-level volume pref: with it at 0 even media in a closed declarative shadow root is silent.
const FIREFOX_MUTE_PREFS = {'media.volume_scale': '0.0'};

function silentOptions(name, options = {}) {
  const merged = {...options, args: silentArgs(name, options.args)};
  if (name === 'firefox') merged.firefoxUserPrefs = {...(options.firefoxUserPrefs || {}), ...FIREFOX_MUTE_PREFS};
  return merged;
}

async function silenceContext(context) {
  await context.addInitScript({path: INIT_SCRIPT_PATH});
  return context;
}

function silenceBrowser(browser) {
  if (browser.__silentBrowser) return browser;
  const newContext = browser.newContext.bind(browser);
  browser.newContext = async (...args) => silenceContext(await newContext(...args));
  // Playwright's own newPage makes a context after the fact, so a script added to it would miss the blank document
  // that setContent and addScriptTag write into. Make the silenced context first, then the page, and close the
  // context with the page the way Playwright's owned context does.
  browser.newPage = async (...args) => {
    const context = await browser.newContext(...args), page = await context.newPage(), pageClose = page.close.bind(page);
    page.close = async (...closeArgs) => { try { await pageClose(...closeArgs); } finally { await context.close(); } };
    return page;
  };
  browser.__silentBrowser = true;
  return browser;
}

async function silentLaunch(engine, options = {}) {
  return silenceBrowser(await engine.launch(silentOptions(engineName(engine), options)));
}

// A persistent context is created with its first page already open, so that page's document is silenced by running
// the init script in it now; every later document and navigation gets it from the context.
async function silentLaunchPersistentContext(engine, userDataDir, options = {}) {
  const context = await silenceContext(await engine.launchPersistentContext(userDataDir, silentOptions(engineName(engine), options)));
  for (const page of context.pages()) await page.evaluate(initScript());
  return context;
}

// A Chrome the tool spawns itself and drives over CDP (no Playwright): the same flag, at the same one place.
function silentChromeArgs(args) {
  const merged = [...args];
  for (const flag of MUTE_ARGS) if (!merged.includes(flag)) merged.push(flag);
  return merged;
}

module.exports = {silentChromeArgs, INIT_SCRIPT_PATH, MUTE_ARGS, FIREFOX_MUTE_PREFS, silentOptions, initScript, silentArgs, silenceContext, silenceBrowser, silentLaunch, silentLaunchPersistentContext};
