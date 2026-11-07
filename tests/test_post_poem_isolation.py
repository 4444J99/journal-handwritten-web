"""Posting regressions for issue #123 after PR #131 (synthetic local repositories only)."""
import os
import subprocess
import unittest
from unittest import mock

import test_post_poem as fixtures

git, make_public, post_poem = fixtures.git, fixtures.make_public, fixtures.post_poem


class PostingIsolationTests(fixtures.Base):
    fake_gh = fixtures.HardenedPostingTests.fake_gh
    edit_j = fixtures.HardenedPostingTests.edit_j
    bare_repo = fixtures.HardenedPostingTests.bare_repo

    def small_build(self):
        out = self.tmp / "output"
        out.mkdir()
        (out / "index.html").write_text("<html>technical fixture</html>\n")
        return out

    def test_git_config_cannot_hide_a_second_push_destination(self):
        self.prepare()
        self.fake_gh()
        clone, bare = make_public(self.tmp)
        second = self.bare_repo("second.git")
        for target in (bare, second):
            git(clone, "config", "--add", "remote.origin.pushurl", str(target))
        config = self.tmp / "spoof.config"
        config.write_text('[remote "origin"]\n'
                          ' url = https://github.com/4444J99/versforms.git\n'
                          f' pushurl = {bare}\n')
        with mock.patch.dict(os.environ, {"GIT_CONFIG": str(config)}):
            code = self.go("p001", "--accept-embedded-font", dry=False, public=clone)
        self.assertEqual(git(second, "for-each-ref", "refs/heads/post"), "", self.out)
        self.assertEqual(git(bare, "for-each-ref", "refs/heads/post"), "", self.out)
        self.assertEqual(code, post_poem.EXIT_STOP, self.out)

    def test_an_empty_additional_push_url_is_rejected_before_any_push(self):
        self.prepare()
        self.fake_gh()
        clone, bare = make_public(self.tmp)
        git(clone, "config", "--add", "remote.origin.pushurl", str(bare))
        git(clone, "config", "--add", "remote.origin.pushurl", "")
        code = self.go("p001", "--accept-embedded-font", dry=False, public=clone)
        self.assertEqual(git(bare, "for-each-ref", "refs/heads/post"), "", self.out)
        self.assertEqual(code, post_poem.EXIT_STOP, self.out)

    def test_push_does_not_change_the_clones_config_or_send_tags(self):
        self.prepare()
        self.fake_gh()
        clone, bare = make_public(self.tmp)
        git(clone, "config", "push.followTags", "true")
        git(clone, "tag", "-a", "private-local-tag", "-m", "fixture", "main")
        before = (clone / ".git" / "config").read_bytes()
        main_before = git(bare, "rev-parse", "main")
        self.assertEqual(self.go("p001", "--accept-embedded-font", dry=False, public=clone), 0, self.out)
        self.assertEqual((clone / ".git" / "config").read_bytes(), before)
        self.assertEqual(git(bare, "tag", "--list"), "")
        self.assertEqual(git(bare, "rev-parse", "main"), main_before)
        self.assertEqual(git(bare, "rev-parse", "post/p001"), git(clone, "rev-parse", "post/p001"))

    def test_mirror_boolean_spellings_and_invalid_values_stop_before_build(self):
        clone, _ = make_public(self.tmp)
        for value in ("on", "true", "1", "yes", "invalid-boolean"):
            with self.subTest(value=value):
                git(clone, "config", "remote.origin.mirror", value)
                with self.local_remote_seam(clone):
                    checks = post_poem.check_public_repo(clone, "post/p001")
                self.assertTrue(any("remote.origin.mirror" in name and not ok for name, ok, _ in checks))
        git(clone, "config", "--unset-all", "remote.origin.mirror")
        with (clone / ".git" / "config").open("a") as f:
            f.write('\n[remote "origin"]\n mirror\n')
        with self.local_remote_seam(clone):
            checks = post_poem.check_public_repo(clone, "post/p001")
        self.assertTrue(any("remote.origin.mirror" in name and not ok for name, ok, _ in checks))
        for value in ("false", "off", "0", "no"):
            with self.subTest(legitimate=value):
                git(clone, "config", "--replace-all", "remote.origin.mirror", value)
                with self.local_remote_seam(clone):
                    checks = post_poem.check_public_repo(clone, "post/p001")
                self.assertTrue(all(ok for _, ok, _ in checks), checks)

    def test_an_explicitly_empty_push_refspec_is_still_a_hard_stop(self):
        clone, _ = make_public(self.tmp)
        git(clone, "config", "remote.origin.push", "")
        with self.local_remote_seam(clone):
            checks = post_poem.check_public_repo(clone, "post/p001")
        self.assertTrue(any(name.startswith("remote.origin.push is not set") and not ok
                            for name, ok, _ in checks))

    def test_failed_worktree_creation_preserves_a_preexisting_branch(self):
        clone, _ = make_public(self.tmp)
        out = self.small_build()
        git(clone, "branch", "post/existing", "main")
        before = git(clone, "for-each-ref")
        with self.assertRaises(RuntimeError):
            post_poem.commit_in_worktree(clone, out, "post/existing", "fixture", self.tmp)
        self.assertEqual(git(clone, "for-each-ref"), before)
        self.assertEqual(git(clone, "status", "--porcelain"), "")
        self.assertEqual(len(git(clone, "worktree", "list").splitlines()), 1)

    def test_git_common_dir_cannot_redirect_worktree_or_blob_verification(self):
        clone, _ = make_public(self.tmp)
        out = self.small_build()
        main_before = git(clone, "rev-parse", "main")
        bad_common = str(self.tmp / "unrelated.git")
        with mock.patch.dict(os.environ, {"GIT_COMMON_DIR": bad_common}):
            sha = post_poem.commit_in_worktree(clone, out, "post/fixture", "fixture", self.tmp)
            self.assertEqual(os.environ["GIT_COMMON_DIR"], bad_common)
        self.assertEqual(git(clone, "rev-parse", "main"), main_before)
        self.assertEqual(git(clone, "rev-parse", "post/fixture"), sha)
        self.assertEqual(git(clone, "status", "--porcelain"), "")
        self.assertEqual(git(clone, "show", "post/fixture:site/index.html"), (out / "index.html").read_text().strip())

    def test_scratch_failure_does_not_change_the_callers_git_environment(self):
        clone, _ = make_public(self.tmp)
        out = self.small_build()
        injected = {"GIT_DIR": str(clone / ".git"), "GIT_INDEX_FILE": str(self.tmp / "index")}
        with mock.patch.dict(os.environ, injected):
            with mock.patch.object(post_poem.tempfile, "mkdtemp", side_effect=OSError("fixture disk full")):
                with self.assertRaises(OSError):
                    post_poem.commit_in_worktree(clone, out, "post/fixture", "fixture", self.tmp)
            self.assertEqual({k: os.environ.get(k) for k in injected}, injected)

    def test_a_whole_spread_without_a_key_has_no_verified_facing_page(self):
        self.prepare(pids=("p003",), public=())
        def unknown_spread(j):
            next(p for p in j["pages"] if p["id"] == "pg3")["sp"] = {
                "s": "whole spread", "cb": None, "f": None, "k": None}
        self.edit_j(unknown_spread)
        for extra in ((), ("--force",)):
            with self.subTest(extra=extra):
                self.assertEqual(self.go("p003", *extra), post_poem.EXIT_STOP, self.out)
                self.assertIn("whole spread", self.out)
                self.assertFalse((self.work / "build").exists())

    def test_an_ordinary_page_without_spread_metadata_remains_usable(self):
        self.prepare(pids=("p003",), public=())
        self.edit_j(lambda j: next(p for p in j["pages"] if p["id"] == "pg3").pop("sp"))
        self.assertEqual(self.go("p003"), post_poem.EXIT_OK, self.out)

    def test_facing_page_ids_in_warnings_stay_out_of_the_public_pr(self):
        self.prepare(release={"p004": {"pool": "series"}})
        def whole(j):
            for page in j["pages"]:
                if page["id"] in ("pg1", "pg2"):
                    page["sp"] = {"s": "whole spread", "cb": None, "f": None, "k": "shared.jpg"}
        self.edit_j(whole)
        clone, _ = make_public(self.tmp)
        code = self.go("p001", "--no-pr", "--accept-shared-scan", "p004", dry=False, public=clone)
        self.assertEqual(code, 0, self.out)
        body = (self.work / "pr-body.md").read_text()
        self.assertNotIn("pg1", body)
        self.assertNotIn("p004", body)
        self.assertIn("pg1", self.out)
        self.assertIn("unpublished version", body)

    def test_credentials_are_redacted_for_dotless_and_ipv6_hosts(self):
        for host in ("localhost", "[::1]", "github.com"):
            for userinfo in ("user:secret", "user:pa@ss/secret"):
                with self.subTest(host=host, userinfo=userinfo):
                    redacted = post_poem._redact(f"https://{userinfo}@{host}/repo")
                    self.assertNotIn("secret", redacted)
                    self.assertNotIn("pa@ss", redacted)
                    self.assertIn(host + "/repo", redacted)
        clean = "https://github.com/4444J99/versforms.git"
        self.assertEqual(post_poem._redact(clean), clean)

    def test_git_errors_do_not_echo_credentials(self):
        result = subprocess.CompletedProcess(["git"], 1, "", "fatal: https://user:secret@localhost/repo refused")
        with mock.patch.object(post_poem.subprocess, "run", return_value=result):
            with self.assertRaises(RuntimeError) as error:
                post_poem.git(self.tmp, "push", "origin", "refs/heads/post/x:refs/heads/post/x")
        self.assertNotIn("secret", str(error.exception))


if __name__ == "__main__":
    unittest.main()
