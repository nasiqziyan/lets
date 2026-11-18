"""Where plans live (the planning root), and the commands that report on it: `lets where` and `lets sync`.

Three homes: plans in the code repo (under plans/), a planning repo for the team, or a private planning repo. A
planning repo can serve a group of code repos. Settings are git config in each repo (lets.*), so nothing extra is
committed to a code repo.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil

from . import settings, ui
from .core import LetsError, git, git_config, run, say
from .paths import ROOT, P, expand, short_path

PLANS = "plans"  # the folder that holds plans inside a code repo
LETS_OPENSPEC_MARK = "Copied into each planning root by `lets setup`"
PLANNING_README = """# Planning

Plans, specs and decisions for {names}, kept by LETS (`lets setup`). The layout is the same as `plans/` in a repo that
keeps its own plans:

- `openspec/`: living specs (`specs/`) and changes (`changes/`, closed ones in `changes/archive/`)
- `epics/<epic>/`: an epic's map, prerequisites, inputs and overview
- `research/`, `questionnaires/`, `docs/adr/`, `GLOSSARY.md`, `CODING_STANDARDS.md`, `CONSTRAINTS.md`
- `additions/`: rules added to LETS commands for these repos (`/lets:add`)
- `repos.json`: the code repos these plans are for

Agents commit here locally after each LETS command; people push when they choose.
"""
IN_REPO_README = """# Plans

This folder holds the plans, specs and decisions for this repo, kept by [LETS](https://www.npmjs.com/package/@nasiq/lets),
the way the team works with coding agents. It's plain Markdown: read it without LETS.

- `openspec/specs/`: how the system behaves now, one folder per capability
- `openspec/changes/`: work in progress, one folder per pull request (closed ones in `changes/archive/`)
- `epics/`: bigger pieces of work, split into several changes
- `docs/adr/`, `GLOSSARY.md`, `CODING_STANDARDS.md`, `CONSTRAINTS.md`: decisions, words and rules
- `additions/`: the team's own steps added to LETS commands

Edit these files in pull requests like any other. The repo's own `docs/` stays where it is.
"""
AGENT_SETUP = [
    "CLAUDE.md",
    "AGENTS.md",
    ".claude/CLAUDE.md",
    ".claude/commands",
    ".claude/agents",
    ".claude/skills",
    ".cursor",
    ".cursorrules",
    ".windsurfrules",
    ".github/copilot-instructions.md",
    ".aider.conf.yml",
]
DOCS_DIRS = ["docs", "doc", "adr", "docs/adr", "docs/decisions"]


def repo_root(cwd: os.PathLike | str | None = None) -> pathlib.Path:
    top = git("rev-parse", "--show-toplevel", cwd=cwd, check=False)
    if not top:
        raise LetsError("Run this inside a git repository.")
    return pathlib.Path(top)


def exclude(root: pathlib.Path, patterns: list[str]) -> None:
    """Keep files out of git in this clone only (.git/info/exclude)."""
    p = pathlib.Path(git("rev-parse", "--git-path", "info/exclude", cwd=root))
    p = p if p.is_absolute() else root / p
    have = p.read_text().splitlines() if p.exists() else []
    added = [line for line in patterns if line not in have]
    if added:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(have + ["# lets"] + added) + "\n")


def in_repo_plans(root: pathlib.Path) -> pathlib.Path:
    return root / PLANS


def uses_lets_here(root: pathlib.Path) -> bool:
    """Does this code repo keep LETS plans in its own plans/ folder?"""
    cfg = in_repo_plans(root) / "openspec" / "config.yaml"
    return cfg.exists() and LETS_OPENSPEC_MARK in cfg.read_text()


def foreign_plans(root: pathlib.Path) -> bool:
    """A plans/ folder that isn't LETS's (LETS won't move into it)."""
    d = in_repo_plans(root)
    return d.exists() and any(d.iterdir()) and not uses_lets_here(root)


def planning_root(root: os.PathLike | str) -> tuple[pathlib.Path | None, str | None]:
    """(planning root, home) for a repo: home is "planning repo", "in-repo", "team" or "private"."""
    root = pathlib.Path(root)
    if git_config("lets.role", root) == "planning":
        return root, "planning repo"
    plans = git_config("lets.plans", root)
    if plans:
        return expand(plans), git_config("lets.sharing", root) or "private"
    if git_config("lets.kind", root) == "own" or uses_lets_here(root):
        return in_repo_plans(root), "in-repo"
    return None, None


def init_planning(proot: pathlib.Path, readme: str | None = None) -> None:
    """The planning layout under a planning root: OpenSpec (none of its own agent files) with LETS's config."""
    from .install import openspec_bin

    proot.mkdir(parents=True, exist_ok=True)
    cfg = proot / "openspec" / "config.yaml"
    if not cfg.exists():
        run(
            [openspec_bin(), "init", "--tools", "none", "--no-animation", "."],
            cwd=proot,
            env=dict(os.environ, CI="1", OPENSPEC_TELEMETRY="0"),
        )
    shutil.copy(str(ROOT / "openspec" / "config.yaml"), str(cfg))
    if readme and not (proot / "README.md").exists():
        (proot / "README.md").write_text(readme)


def git_repos_in(folder: os.PathLike | str) -> list[pathlib.Path]:
    folder = pathlib.Path(folder)
    return sorted(p for p in folder.iterdir() if p.is_dir() and (p / ".git").exists()) if folder.is_dir() else []


def planning_repos_known() -> dict[str, pathlib.Path]:
    """{name: path} of planning repos on this computer (in the folders setup was told about)."""
    out = {}
    for d in settings.plans_dirs():
        for p in git_repos_in(d):
            if git_config("lets.role", p) == "planning":
                out[p.name] = p
    return out


def members(proot: pathlib.Path) -> dict[str, dict]:
    f = proot / "repos.json"
    return json.loads(f.read_text()).get("repos", {}) if f.exists() else {}


def group_of(repo: pathlib.Path) -> tuple[pathlib.Path | None, list[str]]:
    """The planning repo shared by repos next to this one, if any: (path, [member names])."""
    for sib in git_repos_in(repo.parent):
        if sib == repo:
            continue
        plans = git_config("lets.plans", sib)
        if plans and expand(plans).exists():
            return expand(plans), sorted(members(expand(plans)))
    return None, []


def repo_name_from_url(url: str) -> str:
    return re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1].split(":")[-1]) or "plans"


def agent_setup_in(root: pathlib.Path) -> list[str]:
    """Agent setup that isn't LETS's own: files a repo's owners or another tool created."""
    found = [
        rel
        for rel in AGENT_SETUP
        if (root / rel).exists() and not (rel == ".claude/skills" and not any((root / rel).iterdir()))
    ]
    if (root / "openspec").exists():
        found.append("openspec/")
    return found


def repo_settings(root: pathlib.Path) -> dict[str, str]:
    """This repo's build choices, falling back to the profile."""
    from . import profile

    keys = {"build": "lets.build", "tests": "lets.tests", "git": "lets.agents"}
    return {k: git_config(v, root) or profile.answer(k) for k, v in keys.items()}


def additions_for(proot: pathlib.Path | None) -> list[pathlib.Path]:
    """The additions files that apply here: yours, then the team's (committed with the plans)."""
    out = sorted(P.additions.glob("*.md")) if P.additions.exists() else []
    if proot is not None and (proot / "additions").exists():
        out += sorted((proot / "additions").glob("*.md"))
    return out


def cmd_where(a) -> None:
    """Print where this repo's (or this group's) plans live, and how this repo is set up."""
    top = git("rev-parse", "--show-toplevel", check=False)
    if top:
        root = pathlib.Path(top)
        proot, home = planning_root(root)
        if proot is None:
            raise LetsError("This repo isn't set up for LETS yet: run `lets setup`.")
        say("planning root: %s" % proot)
        if home == "planning repo":
            names = sorted(members(root))
            say(
                "code repos:    %s"
                % (
                    ", ".join(
                        "%s (%s)" % (n, short_path(git_config("letsrepo.%s.path" % n, root)) or "not on this computer")
                        for n in names
                    )
                    or "none"
                )
            )
            say("home:          a planning repo")
            return
        name = git_config("lets.repo", root) or root.name
        say("code repo:     %s (%s)" % (root, name))
        group = sorted(members(proot)) if home != "in-repo" else [name]
        if len(group) > 1:
            say("group:         %s" % ", ".join(group))
        say(
            "home:          %s"
            % {
                "in-repo": "plans in this repo",
                "team": "a planning repo for the team",
                "private": "a private planning repo",
            }.get(home or "", home)
        )
        st = repo_settings(root)
        say(
            "team:          %s"
            % (
                "has agreed to agents working here"
                if git_config("lets.kind", root) == "own"
                else "hasn't agreed: leave its AI instructions, docs and GitLab/GitHub alone"
            )
        )
        say("build:         %s · test-first: %s · git: %s" % (st["build"], st["tests"], st["git"]))
        check = git_config("lets.check", root)
        if check:
            say("check:         %s" % check)
        from .walkthrough import base_branch

        bname, how = base_branch(str(root))
        say("base:          %s" % ("%s (%s)" % (bname, how) if bname else how))
        from .profile import PR_NOTE, ai_credit

        mode, trailer, own = ai_credit(root)
        credit = {
            "never": "none: no AI mention in commits or pull requests",
            "trailer": "end each commit message with `%s`" % trailer,
            "trailer-pr": "end each commit message with `%s`, and each pull request description with `%s`"
            % (trailer, PR_NOTE),
        }[mode]
        say("AI credit:     %s (%s)" % (credit, "set for this repo" if own else "your profile"))
    else:
        cwd = pathlib.Path(os.getcwd())
        roots: dict[str, list[str]] = {}
        for r in git_repos_in(cwd):
            plans = git_config("lets.plans", r)
            if plans:
                roots.setdefault(plans, []).append(r.name)
        if len(roots) != 1:
            raise LetsError(
                "Run this inside a repo set up for LETS, or in a folder of repos that share one planning "
                "repo" + (" (these share several: %s)" % ", ".join(roots) if roots else "") + "."
            )
        plans, names = next(iter(roots.items()))
        proot = expand(plans)
        say("planning root: %s" % proot)
        say("code repos:    %s (in %s)" % (", ".join(names), cwd))
        say("home:          a group folder: plan here; build each change in its own repo")
    if top:
        from .upgrade import SETUP_VERSION, is_outdated, set_up_by

        if is_outdated(pathlib.Path(top)):
            say(
                "setup:         by %s: tell me to run `lets setup` here (it asks only what's new in %s)"
                % (set_up_by(pathlib.Path(top)), SETUP_VERSION)
            )
    adds = additions_for(proot)
    if adds:
        say("additions:     %s" % ", ".join(short_path(p) for p in adds))
    if not (proot / "openspec").exists():
        say("warning: no openspec/ in the planning root; run `lets setup` again")


def cmd_sync(a) -> None:
    """Bring a team planning repo up to date (fast-forward only)."""
    top = git("rev-parse", "--show-toplevel", check=False)
    proot, home = planning_root(top) if top else (None, None)
    if proot is None:
        raise LetsError("This repo isn't set up for LETS yet: run `lets setup`.")
    if home == "in-repo":
        ui.ok("Nothing to sync: the plans are in this repo, so `git pull` brings them with the code.")
        return
    if git("rev-parse", "--abbrev-ref", "@{u}", cwd=proot, check=False):
        run(["git", "fetch", "--quiet"], cwd=proot, check=False)
    if not git("rev-parse", "--verify", "--quiet", "@{u}", cwd=proot, check=False):
        ui.ok("The planning repo has no upstream to sync with yet (nothing has been pushed to it).")
        return
    r = run(["git", "pull", "--ff-only", "--quiet"], cwd=proot, check=False)
    if r.returncode == 0:
        ui.ok("Planning repo up to date.")
    else:
        ui.warn(
            "Couldn't fast-forward the planning repo (%s). Sort it out there, then carry on." % r.stderr.strip()[-200:]
        )
