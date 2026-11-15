"""The silent-launch lint sees every bare launch style this repository uses, and the repository has none."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import silent_launch_lint as lint  # noqa: E402


class SilentLaunchLintTests(unittest.TestCase):
    def test_repository_has_no_bare_browser_launch(self):
        self.assertEqual(lint.scan(ROOT), [])

    def test_sees_playwright_launches_however_the_engine_is_named(self):
        for line in ("browser = await chromium.launch({headless:true});",
                     "const b = await playwright.webkit.launch();",
                     "browser = await playwright[engine].launch({headless:true});",
                     "await browserType.launchPersistentContext(dir, {});",
                     "const b = await firefox.connectOverCDP(url);",
                     "p.chromium.launch()"):
            self.assertEqual(lint.bare_launches(line), [1], line)

    def test_sees_aliased_split_and_destructured_launches(self):
        for source, line in (("await chromium\n  .launch({headless:true});", 2),
                             ("const runner = chromium;\nawait runner.launch();", 2),
                             ("const {chromium: runner} = require('playwright');\nawait runner.launch();", 2),
                             ("await chromium['launch']();", 1),
                             ("const {launch} = chromium;\nawait launch();", 1)):
            self.assertEqual(lint.bare_launches(source), [line], source)
        self.assertEqual(lint.bare_launches("runner = pw.chromium\nrunner.launch()\n", python=True), [2])
        self.assertEqual(lint.bare_launches("getattr(pw, name).launch()\n", python=True), [1])
        self.assertEqual(lint.bare_launches("/* webkit.launch() */ const x = 1;"), [])
        self.assertEqual(lint.bare_launches("await engine.launch(id);"), [])

    def test_sees_a_headless_chrome_spawn_that_skips_the_helper(self):
        self.assertEqual(lint.bare_launches("spawn(CHROME, ['--headless=new', '--no-first-run']);"), [1])
        self.assertEqual(lint.bare_launches('const args = [\n  "--headless=new",\n  "about:blank",\n];'), [2])

    def test_accepts_the_helper_and_unrelated_launch_names(self):
        for line in ("browser = await silentLaunch(chromium, {headless:true});",
                     "browser = await silentLaunch(playwright[engine], {headless:true});",
                     "spawn(CHROME, silentChromeArgs(['--headless=new', '--no-first-run']));",
                     "const args = silentChromeArgs([\n  '--headless=new',\n  'about:blank',\n]);",
                     "await lab.launch(id);",
                     "async function launch() {",
                     "// chromium.launch({headless:true})",
                     "//   2. launches Chrome headless with a throw-away profile"):
            self.assertEqual(lint.bare_launches(line), [], line)


if __name__ == "__main__":
    unittest.main()
