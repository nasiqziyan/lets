"""Keeping repos in step with LETS: which version set a repo up, and which repos an older version set up.

Each repo records the version of the setup questions it was set up with (`lets.version`). When a release adds or
changes a setup question, SETUP_VERSION moves to that release; repos set up before it are outdated until `lets setup`
runs in them again, which asks only what's new and keeps the other answers."""

from __future__ import annotations

import json
import pathlib

from . import settings
from .core import git, git_config
from .paths import expand, tilde

SETUP_VERSION = "1.1.0"  # the release that last changed the setup questions


def parse(v: str | None) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in (v or "0").split("."))
    except ValueError:
        return (0,)


def repo_version(r: pathlib.Path) -> str | None:
    return git_config("lets.version", r) or None


def is_outdated(r: pathlib.Path) -> bool:
    """Set up (it has `lets.kind`) by setup questions older than this release's."""
    return (
        bool(git_config("lets.kind", r))
        and git_config("lets.role", r) != "planning"
        and parse(repo_version(r)) < parse(SETUP_VERSION)
    )


def remember_repo(r: pathlib.Path) -> None:
    data = settings.load()
    known = data.setdefault("repos", [])
    if tilde(r) not in known:
        known.append(tilde(r))
        settings.save(data)


def known_repos() -> list[pathlib.Path]:
    """Code repos LETS set up on this computer: the ones setup remembered, and the ones planning repos list."""
    out = {expand(p) for p in settings.load().get("repos", []) if p}
    from .planning import git_repos_in

    for d in settings.plans_dirs():
        for proot in git_repos_in(d):
            for line in git("config", "--get-regexp", r"^letsrepo\..*\.path$", cwd=proot, check=False).splitlines():
                out.add(pathlib.Path(line.split(" ", 1)[1]))
    return sorted(p for p in out if (p / ".git").exists())


def outdated_repos() -> list[pathlib.Path]:
    return [r for r in known_repos() if is_outdated(r)]


def set_up_by(r: pathlib.Path) -> str:
    """Which LETS set a repo up, in words: "LETS 1.1.0", or "an earlier LETS" (before versions were recorded)."""
    v = repo_version(r)
    return "LETS %s" % v if v else "an earlier LETS"


def describe(r: pathlib.Path) -> str:
    v = repo_version(r)
    return "%s (LETS %s)" % (tilde(r), v) if v else tilde(r)


def remove_attribution_file(r: pathlib.Path) -> bool:
    """Take out the per-repo Claude Code settings that setup before 1.1.0 wrote for private plans (the global
    settings already cover them). Keeps anything else in the file; deletes it only if nothing else is left."""
    local = r / ".claude" / "settings.local.json"
    if not local.exists():
        return False
    try:
        data = json.loads(local.read_text() or "{}")
    except ValueError:
        return False
    if "attribution" not in data and "includeCoAuthoredBy" not in data:
        return False
    data.pop("attribution", None)
    data.pop("includeCoAuthoredBy", None)
    if data:
        local.write_text(json.dumps(data, indent=2) + "\n")
    else:
        local.unlink()
        if not any(local.parent.iterdir()):
            local.parent.rmdir()
    return True
