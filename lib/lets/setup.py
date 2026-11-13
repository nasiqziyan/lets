"""`lets setup`: set up one repo, or several related repos that share their plans. Guided; flags answer its
questions for scripts. Re-run it any time to change a repo's choices, or to move its plans to another home."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re

from . import profile, settings, ui
from .changes import Change, agree, json_of
from .core import LetsError, git, git_config, run
from .install import folder_changes
from .paths import P, expand, short_path, tilde
from .planning import (
    DOCS_DIRS,
    IN_REPO_README,
    PLANNING_README,
    agent_setup_in,
    exclude,
    foreign_plans,
    git_repos_in,
    group_of,
    in_repo_plans,
    init_planning,
    members,
    planning_repos_known,
    planning_root,
    repo_name_from_url,
    repo_root,
    uses_lets_here,
)

REPO_QUESTIONS = {
    "build": "How do you want to build in %s?",
    "tests": "Test-first in %s: write a failing test before the code that makes it pass?",
    "git": "How far may agents go with git in %s?",
}
DEFAULTS = dict(
    mode=None,
    path=None,
    repos=None,
    planning=None,
    url=None,
    plans_dir=None,
    build=None,
    tests=None,
    agents=None,
    check=None,
    base=None,
    ai_credit=None,
    yes=False,
    remove=False,
)


def setup_args(**kw) -> argparse.Namespace:
    return argparse.Namespace(**dict(DEFAULTS, **kw))


def suggest_check(root: pathlib.Path) -> str | None:
    """A quick check this repo probably has (lint, types or fast tests)."""
    pj = root / "package.json"
    if pj.exists():
        try:
            scripts = json.loads(pj.read_text()).get("scripts", {})
        except ValueError:
            scripts = {}
        for name in ("check", "lint", "typecheck", "test"):
            if name in scripts:
                return "npm run -s %s" % name
    if (root / "Makefile").exists() and re.search(r"^check:", (root / "Makefile").read_text(errors="replace"), re.M):
        return "make check"
    if ((root / "pyproject.toml").exists() or (root / "setup.cfg").exists()) and (root / "tests").exists():
        return "python -m pytest -q"
    return None


def choice_for_repo(key: str, flag: str | None, label: str, current: str) -> str:
    """A per-repo build choice: the flag if given, else asked with the repo's (or the profile's) answer as default."""
    if flag:
        return flag
    c = profile.choice(key)
    return ui.select(
        REPO_QUESTIONS[key] % label,
        [(o.key, o.label, o.hint) for o in c.options],
        current or profile.answer(key),
        "Your profile's answer is chosen already." if not current else "This repo's current answer is chosen already.",
    )


def credit_flag(flag: str | None) -> str | None:
    """--ai-credit: never, trailer or trailer-pr (with your profile's trailer, or `trailer:<line>`), or profile to
    follow your profile again. None: leave the repo's setting as it is. Returns the git config value ("" to unset)."""
    if flag is None:
        return None
    if flag == "profile":
        return ""
    mode, _, line = flag.partition(":")
    if mode not in ("never", "trailer", "trailer-pr") or (mode == "never" and line):
        raise LetsError("--ai-credit takes never, trailer, trailer-pr (or trailer:<line>), or profile.")
    if mode == "never":
        return "never"
    return "%s:%s" % (mode, line.strip() or profile.ai_credit()[1] or profile.TRAILERS[0])


def cmd_setup(a: argparse.Namespace) -> None:
    for k, v in DEFAULTS.items():
        if not hasattr(a, k):
            setattr(a, k, v)
    if a.remove:
        root = repo_root()
        git("config", "--remove-section", "lets", cwd=root, check=False)
        ui.ok("Removed this repo's LETS settings. Its plans are left where they are.")
        return
    screen = ui.title if ui.interactive() else (lambda *_: None)
    here = git("rev-parse", "--show-toplevel", check=False)
    if here and git_config("lets.role", here) == "planning":
        raise LetsError("This is a planning repo; run `lets setup` in (or for) the code repos it plans for.")

    # 1. What are you setting up?
    screen("LETS setup", "1 · what")
    cwd = pathlib.Path(os.getcwd())
    near = git_repos_in(pathlib.Path(here).parent) if here else git_repos_in(cwd)
    mode = a.mode or ui.select(
        "What are you setting up?",
        [
            (
                "one",
                "One repo",
                "a single git repo (a monorepo counts as one)" + (" · %s" % os.path.basename(here) if here else ""),
            ),
            ("group", "Several related repos", "separate git repos that share their plans"),
        ],
        "one" if here or len(near) < 2 else "group",
    )
    if mode == "one":
        if a.path:
            here = git("rev-parse", "--show-toplevel", cwd=os.path.expanduser(a.path), check=False)
        elif not here:
            p = ui.text("Which repo do you want to set up?", None, paths=True, required=True)
            here = git("rev-parse", "--show-toplevel", cwd=os.path.expanduser(p or "."), check=False)
        if not here:
            raise LetsError("That isn't a git repo.")
        repos = [pathlib.Path(here).resolve()]
        folder = repos[0].parent
    else:
        start = a.path or (str(pathlib.Path(here).parent) if here else str(cwd))
        folder = pathlib.Path(
            os.path.expanduser(
                start if a.path else ui.text("Which folder holds the repos?", short_path(start), paths=True) or start
            )
        ).resolve()
        found = [p for p in git_repos_in(folder) if git_config("lets.role", p) != "planning"]
        if not found:
            raise LetsError("No git repos found in %s." % short_path(folder))
        picked = (
            a.repos.split(",")
            if a.repos
            else ui.multiselect(
                "Which repos in %s should share the plans?" % short_path(folder), [(p.name, p.name) for p in found]
            )
        )
        repos = [p for p in found if p.name in picked]
        if not repos:
            raise LetsError("No repos chosen.")

    # 2. Where should the plans live?
    screen("LETS setup", "2 · plans")
    for d in DOCS_DIRS:
        hits = [r.name for r in repos if (r / d).is_dir()]
        if hits:
            ui.note("Found %s/ in %s: LETS leaves it in place, and agents will read it." % (d, ", ".join(hits)))
            break
    was = {r.name: planning_root(r) for r in repos}
    joined, planning = None, a.planning
    if mode == "one" and not planning:
        gp, names = group_of(repos[0])
        if gp is not None and not git_config("lets.plans", repos[0]):
            if ui.confirm(
                "%s sits next to repos that share the planning repo %s. Join it?" % (repos[0].name, gp.name),
                True,
                "Join %s" % gp.name,
                "Set it up on its own",
                "plan it together with " + ", ".join(names),
            ):
                joined = gp
                planning = git_config("lets.sharing", gp) or "team"
    if not planning:
        current = was[repos[0].name][1] if mode == "one" else None
        opts = (
            [("in-repo", "In this repo", "in plans/, committed with the code: your repo, or a team that uses LETS")]
            if mode == "one"
            else []
        ) + [
            ("team", "In a planning repo for the team", "the team uses LETS, but keeps plans apart from the code"),
            ("private", "In a private planning repo", "the team doesn't use LETS: only you see the plans"),
        ]
        planning = ui.select(
            "LETS keeps planning files: plans, specs and decisions. Where should they live?",
            opts,
            current if current in ("in-repo", "team", "private") else ("private" if mode == "one" else "team"),
        )
    if planning == "in-repo":
        if mode != "one":
            raise LetsError("Plans can live in the repo only when you set up one repo.")
        if foreign_plans(repos[0]):
            raise LetsError(
                "%s already has a plans/ folder that isn't LETS's. LETS keeps its plans there, so it won't "
                "mix with it: rename that folder, or choose a planning repo instead." % repos[0].name
            )
        others = agent_setup_in(repos[0])
        if others and not uses_lets_here(repos[0]):
            raise LetsError(
                "%s already has agent setup (%s). LETS is for repos without one, so it won't add its "
                "plans here. Choose a planning repo instead, or remove that setup first."
                % (repos[0].name, ", ".join(others))
            )
    else:
        found = {r.name: agent_setup_in(r) for r in repos}
        found = {k: v for k, v in found.items() if v}
        if found:
            ui.warn(
                "Agent setup found: %s. LETS leaves it untouched and doesn't merge with it."
                % "; ".join("%s: %s" % (k, ", ".join(v)) for k, v in found.items())
            )
            if not (a.yes or ui.confirm("Do you want to set up LETS beside it anyway?", False)):
                raise LetsError("Nothing was changed.")

    # 3. The planning repo, if separate
    url, dest = a.url, joined
    if planning in ("team", "private") and dest is None:
        old_root, old_home = was[repos[0].name]
        if mode == "one" and old_home == planning and old_root is not None and old_root.exists() and not url:
            dest = old_root
        else:
            dest, url = choose_planning_repo(a, planning, mode, folder)

    # 4. Per-repo choices
    screen("LETS setup", "3 · how you'll work")
    label = repos[0].name if len(repos) == 1 else "these repos"
    cur = (lambda key: git_config(key, repos[0])) if len(repos) == 1 else (lambda key: "")
    build = choice_for_repo("build", a.build, label, cur("lets.build"))
    tests = choice_for_repo("tests", a.tests, label, cur("lets.tests"))
    agents = choice_for_repo("git", a.agents, label, cur("lets.agents"))
    checks = {}
    for r in repos:
        if a.check is not None:
            checks[r.name] = a.check
            continue
        guess = git_config("lets.check", r) or suggest_check(r) or ""
        checks[r.name] = (
            ui.text(
                "Which quick check should run before reviews in %s?" % r.name,
                guess or None,
                explain="Lint, types or fast tests, taking a minute or two at most. Leave it blank for none.",
            )
            or ""
            if ui.interactive()
            else guess
        )

    bases = {r.name: ask_base(r, a.base) for r in repos}
    credit = credit_flag(a.ai_credit)

    # 5. Moving plans from their old home, if the home changed
    from . import move

    moves = [
        m
        for m in (
            move.plan_for(r, was[r.name], planning, in_repo_plans(r) if planning == "in-repo" else dest) for r in repos
        )
        if m
    ]

    # 6. The changes, shown and agreed
    changes = setup_changes(repos, planning, url, dest, build, tests, agents, checks, bases, credit)
    for m in moves:
        changes.append(m.change())
    agree(changes, "setup", a.yes, one_by_one=False)
    for m in moves:
        m.finish()
    proot = in_repo_plans(repos[0]) if planning == "in-repo" or dest is None else dest
    ui.out()
    ui.ok("Set up %s · plans: %s" % (", ".join(r.name for r in repos), short_path(proot)))
    if len(repos) > 1:
        ui.step(
            "open Claude Code (or Codex) in %s and run /lets:next. Plan work that spans the repos there with "
            "/lets:epic-start <name>; for one piece of work, run /lets:change-start <name> inside its repo."
            % short_path(folder)
        )
    else:
        ui.step(
            "open Claude Code (or Codex) in this repo and run /lets:next, or /lets:change-start <name> for one "
            "piece of work."
        )


def ask_base(r: pathlib.Path, flag: str | None) -> str | None:
    """The branch work in this repo merges into: the flag (`auto` clears it), else what's set, else asked only when
    it can't be told (no remote default branch, and more than one usual trunk). None leaves it to detection."""
    from .walkthrough import CANDIDATES

    if flag is not None:
        return None if flag in ("", "auto") else flag
    current = git_config("lets.base", r)
    if current:
        return current
    if git("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", cwd=r, check=False):
        return None
    trunks = [
        n
        for n in CANDIDATES
        if git("rev-parse", "--verify", "--quiet", n, cwd=r, check=False)
        or git("rev-parse", "--verify", "--quiet", "origin/" + n, cwd=r, check=False)
    ]
    if len(trunks) < 2 or not ui.interactive():
        return None
    return ui.select(
        "Which branch does work in %s merge into?" % r.name,
        [(n, n, "") for n in trunks],
        trunks[0],
    )


def choose_planning_repo(
    a: argparse.Namespace, planning: str, mode: str, folder: pathlib.Path
) -> tuple[pathlib.Path, str | None]:
    """Join or create a planning repo: one already on this computer, or one cloned from its URL."""
    url = a.url
    known = {
        n: p for n, p in planning_repos_known().items() if (git_config("lets.sharing", p) or "private") == planning
    }
    have = "join"
    if planning == "team" and not url and ui.interactive():
        have = ui.select(
            "Does your team already have a planning repo?",
            [
                ("join", "Yes, join it", "you'll paste its clone URL"),
                ("create", "No, create it now", "from an empty project you make for it"),
            ],
            "join",
        )
    if not url and known and have == "join" and ui.interactive():
        pick = ui.select(
            "Is it one of the team planning repos already on this computer?"
            if planning == "team"
            else "Do you want to use a private planning repo that's already on this computer?",
            [(n, n, short_path(p)) for n, p in known.items()]
            + [("new", "No, another one" if planning == "team" else "No, a new one", "you'll paste its clone URL")],
            "new",
        )
        if pick != "new":
            return known[pick], None
    if not url:
        ui.note(
            "Paste the clone URL of your team's planning repo, from GitLab or GitHub."
            if planning == "team" and have == "join"
            else "Make an empty project for it on GitLab or GitHub that your team can see, then paste its clone URL."
            if planning == "team"
            else "Make an empty private project for it on GitLab or GitHub, then paste its clone URL."
        )
        url = ui.text("What is the planning repo's clone URL?", None, required=True)
        if not url:
            raise LetsError("A separate planning repo needs its clone URL: --url <clone URL>.")
    dirs = settings.plans_dirs()
    default_dir = str(folder) if mode == "group" else str(dirs[0] if dirs else P.home / "plans")
    where = a.plans_dir or ui.text(
        "Where should planning repos be kept on this computer?", short_path(default_dir), paths=True
    )
    return expand(where or default_dir).resolve() / repo_name_from_url(url), url


def setup_changes(
    repos: list[pathlib.Path],
    planning: str,
    url: str | None,
    dest: pathlib.Path | None,
    build: str,
    tests: str,
    agents: str,
    checks: dict[str, str],
    bases: dict[str, str | None] | None = None,
    credit: str | None = None,
) -> list[Change]:
    """Everything setup would change, as Changes (made only once agreed)."""
    changes: list[Change] = []
    if planning != "in-repo":
        assert dest is not None

        def make_planning_repo(dest: pathlib.Path = dest, url: str | None = url, sharing: str = planning) -> None:
            if not (dest / ".git").exists():
                if dest.exists() and any(dest.iterdir()):
                    raise LetsError("%s exists and isn't a git repo. Move it, then re-run." % short_path(dest))
                dest.parent.mkdir(parents=True, exist_ok=True)
                r = run(["git", "clone", "--quiet", url, str(dest)], check=False)
                if r.returncode != 0:
                    raise LetsError("Couldn't clone %s: %s" % (url, r.stderr.strip()))
            for k, v in (
                ("lets.role", "planning"),
                ("lets.kind", "own"),
                ("lets.agents", "commit"),
                ("lets.sharing", sharing),
            ):
                git("config", k, v, cwd=dest)
            init_planning(dest)
            group = members(dest)
            for r in repos:
                group[r.name] = {"remote": git("remote", "get-url", "origin", cwd=r, check=False) or ""}
                git("config", "letsrepo.%s.path" % r.name, str(r), cwd=dest)
            (dest / "repos.json").write_text(json.dumps({"repos": group}, indent=2, sort_keys=True) + "\n")
            (dest / "README.md").write_text(PLANNING_README.format(names=", ".join(sorted(group))))
            exclude(dest, [".lets/"])
            git("add", "-A", cwd=dest)
            if git("status", "--porcelain", cwd=dest):
                if not git("rev-parse", "--verify", "--quiet", "HEAD", cwd=dest, check=False):
                    git("checkout", "-q", "-B", "main", cwd=dest, check=False)
                run(
                    ["git", "commit", "-q", "--no-verify", "-m", "lets setup: plans for %s" % ", ".join(sorted(group))],
                    cwd=dest,
                )

        names = ", ".join(r.name for r in repos)
        summary = (
            ("add %s to this planning repo" % names)
            if (dest / ".git").exists()
            else ("clone the planning repo, set out its folders, and add %s" % names)
        )
        changes.append(
            Change(
                dest,
                summary,
                apply=make_planning_repo,
                details="%s; openspec/, repos.json and README.md, committed locally (not pushed)"
                % (url or "existing repo"),
            )
        )
        if tilde(dest.parent) not in [tilde(d) for d in settings.plans_dirs()]:
            changes.append(
                Change(
                    P.settings,
                    "remember that planning repos live in %s" % short_path(dest.parent),
                    apply=lambda d=dest.parent: settings.remember_plans_dir(d),
                )
            )
            changes += folder_changes([str(dest.parent)], "planning repos in %s" % short_path(dest.parent))
    for r in repos:

        def configure(r: pathlib.Path = r) -> None:
            values = {
                "lets.kind": "other" if planning == "private" else "own",
                "lets.build": build,
                "lets.tests": tests,
                "lets.agents": agents,
                "lets.repo": r.name,
            }
            if planning != "in-repo" and dest is not None:
                values["lets.plans"] = tilde(dest)
                values["lets.sharing"] = planning
            for k, v in values.items():
                git("config", k, v, cwd=r)
            if planning == "in-repo":
                for k in ("lets.plans", "lets.sharing"):
                    git("config", "--unset", k, cwd=r, check=False)
            if checks.get(r.name):
                git("config", "lets.check", checks[r.name], cwd=r)
            else:
                git("config", "--unset", "lets.check", cwd=r, check=False)
            if (bases or {}).get(r.name):
                git("config", "lets.base", (bases or {})[r.name], cwd=r)
            else:
                git("config", "--unset", "lets.base", cwd=r, check=False)
            if credit:
                git("config", "lets.ai-credit", credit, cwd=r)
            elif credit == "":
                git("config", "--unset", "lets.ai-credit", cwd=r, check=False)
            exclude(r, [".lets/"])
            if planning == "private":
                local = r / ".claude" / "settings.local.json"
                data = json_of(local)
                data["attribution"] = {"commit": "", "pr": ""}
                data["includeCoAuthoredBy"] = False
                local.parent.mkdir(exist_ok=True)
                local.write_text(json.dumps(data, indent=2) + "\n")
                exclude(r, [".claude/settings.local.json", "CLAUDE.local.md"])
                if (
                    (r / "AGENTS.md").exists()
                    and not (r / "CLAUDE.md").exists()
                    and not (r / ".claude" / "CLAUDE.md").exists()
                    and not (r / "CLAUDE.local.md").exists()
                ):
                    (r / "CLAUDE.local.md").write_text(
                        "<!-- lets: loads this repo's AGENTS.md in Claude Code; stays out of git -->\n@AGENTS.md\n"
                    )
            if planning == "in-repo":
                init_planning(in_repo_plans(r), IN_REPO_README)

        what = ["settings (git config; nothing committed)"]
        if planning == "in-repo":
            what.append("plans/ for its plans")
        if planning == "private":
            what.append("no AI attribution from Claude Code (a private settings file)")
        changes.append(
            Change(
                r,
                "; ".join(what),
                apply=configure,
                details="git config lets.*: plans %s, build %s, "
                "test-first %s, git %s%s"
                % (planning, build, tests, agents, (", check '%s'" % checks[r.name]) if checks.get(r.name) else ""),
            )
        )
    return changes
