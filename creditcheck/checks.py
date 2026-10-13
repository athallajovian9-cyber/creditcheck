"""creditcheck: did the merge keep the contributor's name?

Two rules, one incident each:

- creditless-rebase : a contribution was re-authored under someone else's
                      name with no Co-authored-by trailer. This happened
                      for real: a 49-line test contribution was merged as
                      the maintainer's own squash commit, and the original
                      author vanished from the contributors graph until a
                      trailer was requested by hand.
- creditless-squash : a commit that closes a PR (#123 suffix) carries only
                      the merger's identity. GitHub attributes the squash
                      to whoever presses merge unless the PR author rides
                      along - worth a look before the contributor list
                      lies.

Pure git log parsing. No network.
"""

from __future__ import annotations

import re
import subprocess
from typing import List, Sequence

from .finding import Finding

_LOG_FORMAT = "%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e"

_SQUASH_SUFFIX = re.compile(r"\(#(\d+)\)\s*$")
_TRAILER_COAUTHOR = re.compile(r"^co-authored-by:\s*(.+)$", re.I | re.M)


def _commits(repo: str) -> List[dict]:
    out = subprocess.run(
        ["git", "-C", repo, "log", f"--format={_LOG_FORMAT}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if out.returncode != 0:
        return []
    commits = []
    for rec in out.stdout.split("\x1e"):
        rec = rec.strip("\n")
        if "\x1f" not in rec:
            continue
        sha, an, ae, cn, ce, body = rec.split("\x1f", 5)
        commits.append({
            "sha": sha.strip(), "author_name": an, "author_email": ae,
            "committer_name": cn, "committer_email": ce, "body": body,
        })
    return commits


def _mentioned(body: str, name: str, email: str) -> bool:
    for m in _TRAILER_COAUTHOR.finditer(body):
        who = m.group(1).strip().lower()
        if name.strip().lower() in who or email.strip().lower() in who:
            return True
    return False


def _short(sha: str) -> str:
    return sha[:7]


def creditless_rebase(lines: Sequence[str], path: str, *, repo: str = "."):
    for c in _commits(repo):
        if c["author_email"] == c["committer_email"]:
            continue
        if _mentioned(c["body"], c["author_name"], c["author_email"]):
            continue
        subject = c["body"].strip().splitlines()[0] if c["body"].strip() else ""
        yield Finding(
            "creditless-rebase", "error", repo, 0,
            f"commit {_short(c['sha'])} (\"{subject[:60]}\") was authored by "
            f"{c['author_name']} <{c['author_email']}> but committed as "
            f"{c['committer_name']} without a Co-authored-by trailer: the "
            "author will not appear in the contributors graph.",
        )


def creditless_squash(lines: Sequence[str], path: str, *, repo: str = "."):
    for c in _commits(repo):
        subject = c["body"].strip().splitlines()[0] if c["body"].strip() else ""
        m = _SQUASH_SUFFIX.search(subject)
        if not m:
            continue
        if c["author_email"] != c["committer_email"]:
            continue  # already covered by creditless-rebase
        if _mentioned(c["body"], c["author_name"], c["author_email"]):
            continue
        yield Finding(
            "creditless-squash", "warning", repo, 0,
            f"commit {_short(c['sha'])} looks like a squash-merged PR "
            f"(#{m.group(1)}) carrying only {c['committer_name']}'s "
            "identity. If the PR had another author, their name is missing "
            "here - check and add a Co-authored-by trailer.",
        )


CHECKS = {
    "creditless-rebase": (creditless_rebase, "error"),
    "creditless-squash": (creditless_squash, "warning"),
}

CHECK_DOCS = {
    "creditless-rebase": "author != committer and no Co-authored-by trailer",
    "creditless-squash": "squash commit (#N) with only the merger's identity",
}
