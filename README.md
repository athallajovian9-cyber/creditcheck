# creditcheck

**Did the merge keep the contributor's name?**

Squash-merging re-authors a pull request under whoever presses the merge
button. GitHub then draws the contributors graph from that commit — so
without a `Co-authored-by` trailer, the person who wrote the code
disappears from your project's history. It has happened: a 49-line test
contribution was merged as the maintainer's own commit, and the author
only got credit after asking for it.

creditcheck reads `git log` and flags exactly that, with no network:

```console
$ creditcheck
. error: [creditless-rebase] commit a1b2c3d ("add directory-search tests") was authored by some <s@s> but committed as maintainer <m@m> without a Co-authored-by trailer: the author will not appear in the contributors graph.
. warning: [creditless-squash] commit d4e5f6g looks like a squash-merged PR (#17) carrying only maintainer's identity...
creditcheck: 1 error(s), 1 warning(s)
```

## Checks

| check | fires when |
|---|---|
| `creditless-rebase` | author != committer and no matching `Co-authored-by` trailer — credit is lost |
| `creditless-squash` | commit subject ends `(#123)` with only the merger's identity — verify before the graph lies |

## Install

```console
$ pip install creditcheck       # PyPI
$ npm install -g creditcheck    # npm (same Python core via a Node launcher)
```

From source — zero dependencies, Python 3.9+:

```console
$ pip install git+https://github.com/athallajovian9-cyber/creditcheck
$ python -m creditcheck path/to/repo
```

## Usage

```console
$ creditcheck --list-checks
creditless-rebase    [error  ] author != committer and no Co-authored-by trailer
creditless-squash    [warning] squash commit (#N) with only the merger's identity

$ creditcheck . --format json
$ creditcheck --fail-on warning .   # CI-strict
```

Run it in CI on every merge to keep the contributors graph honest.

## Contributing

Issue first, then one check function + one test. Credit policy in
[CONTRIBUTORS.md](CONTRIBUTORS.md), workflow in
[CONTRIBUTING.md](CONTRIBUTING.md). Tests must build real git repos with
mixed identities — no network, no mocks of git itself.

## License

MIT
