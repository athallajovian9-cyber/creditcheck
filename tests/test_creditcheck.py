"""Tests against real temporary git repositories with mixed identities."""

from __future__ import annotations

import os
import subprocess

from creditcheck.engine import lint


BASE_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Maintainer", "GIT_AUTHOR_EMAIL": "m@m",
    "GIT_COMMITTER_NAME": "Maintainer", "GIT_COMMITTER_EMAIL": "m@m",
}


def git(repo, *args, author=None, committer=None):
    env = dict(BASE_ENV)
    if author:
        env["GIT_AUTHOR_NAME"], env["GIT_AUTHOR_EMAIL"] = author
    if committer:
        env["GIT_COMMITTER_NAME"], env["GIT_COMMITTER_EMAIL"] = committer
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, capture_output=True, env=env,
    )


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "a.txt").write_text("seed\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "seed")
    return repo


class TestCreditlessRebase:
    def test_clean_repo_is_quiet(self, tmp_path):
        assert lint(str(make_repo(tmp_path))) == []

    def test_reauthored_commit_without_trailer_is_flagged(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "b.txt").write_text("work\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "add contributor work",
            author=("Contributor", "c@c"),
            committer=("Maintainer", "m@m"))
        findings = lint(str(repo))
        rebased = [f for f in findings if f.rule == "creditless-rebase"]
        assert len(rebased) == 1
        assert rebased[0].severity == "error"
        assert "Contributor" in rebased[0].message
        assert "Co-authored-by" in rebased[0].message

    def test_reauthored_commit_with_trailer_is_quiet(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "c.txt").write_text("work\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "add contributor work\n\nCo-authored-by: Contributor <c@c>",
            author=("Contributor", "c@c"),
            committer=("Maintainer", "m@m"))
        assert lint(str(repo)) == []

    def test_trailer_by_email_alone_is_quiet(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "d.txt").write_text("work\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "add work\n\nCo-authored-by: Someone <c@c>",
            author=("Contributor", "c@c"),
            committer=("Maintainer", "m@m"))
        assert lint(str(repo)) == []


class TestCreditlessSquash:
    def test_squash_without_other_identity_warns(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "e.txt").write_text("work\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "fix the parser (#42)")
        findings = lint(str(repo))
        squash = [f for f in findings if f.rule == "creditless-squash"]
        assert len(squash) == 1
        assert squash[0].severity == "warning"
        assert "#42" in squash[0].message

    def test_plain_commit_is_not_a_squash(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "f.txt").write_text("work\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "a normal subject with (parens)")
        assert lint(str(repo)) == []

    def test_rebased_squash_is_only_reported_once(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "g.txt").write_text("work\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "fix things (#7)",
            author=("Contributor", "c@c"),
            committer=("Maintainer", "m@m"))
        findings = lint(str(repo))
        assert [f.rule for f in findings] == ["creditless-rebase"]


class TestCli:
    def run_cli(self, *args):
        import sys
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return subprocess.run(
            [sys.executable, "-m", "creditcheck", *args],
            capture_output=True, text=True, cwd=root,
        )

    def test_failing_repo_exits_one(self, tmp_path):
        repo = make_repo(tmp_path)
        (repo / "h.txt").write_text("work\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "stolen work",
            author=("Contributor", "c@c"),
            committer=("Maintainer", "m@m"))
        r = self.run_cli(str(repo))
        assert r.returncode == 1
        assert "creditless-rebase" in r.stdout

    def test_json_output(self, tmp_path):
        import json
        repo = make_repo(tmp_path)
        (repo / "i.txt").write_text("work\n", encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "stolen work",
            author=("Contributor", "c@c"),
            committer=("Maintainer", "m@m"))
        r = self.run_cli(str(repo), "--format", "json")
        data = json.loads(r.stdout)
        assert data[0]["rule"] == "creditless-rebase"

    def test_list_checks(self):
        r = self.run_cli("--list-checks")
        assert r.returncode == 0
        assert "creditless-squash" in r.stdout
