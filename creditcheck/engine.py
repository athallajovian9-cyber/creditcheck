"""creditcheck: did the merge keep the contributor's name?"""

from __future__ import annotations

import os
from typing import List, Sequence

from .checks import CHECKS
from .finding import Finding


def lint(repo: str = ".", disabled: Sequence[str] = ()) -> List[Finding]:
    findings: List[Finding] = []
    for rule_id, (fn, _severity) in CHECKS.items():
        if rule_id in disabled:
            continue
        findings.extend(fn([], repo, repo=repo))
    findings.sort(key=lambda f: (f.rule, f.path))
    return findings
