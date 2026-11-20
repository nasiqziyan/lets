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
from .upgrade import SETUP_VERSION, is_outdated, remember_repo, remove_attribution_file, set_up_by

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
    team_agreed=None,
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


def choice_for_repo(key: str, flag: str | None, label: str, current: str, hide: tuple[str, ...] = ()) -> str:
    """A per-repo build choice: the flag if given, else asked with the repo's (or the profile's) answer as default.
    Options in `hide` aren't offered (and fall back to the first that is)."""
    c = profile.choice(key)
    keys = [o.key for o in c.options if o.key not in hide]
    if flag:
        if flag in hide:
            raise LetsError("%s isn't available here: %s" % (flag, TEAM_NOT_AGREED_SHIP))
        return flag
    default = current or profile.answer(key)
    if default not in keys:
        default = keys[-1]
    if not ui.interactive():
        return default
    return ui.select(
        REPO_QUESTIONS[key] % label,
        [(o.key, o.label, o.hint) for o in c.options if o.key in keys],
        default,
        "Your profile's answer is chosen already." if not current else "This repo's current answer is chosen already.",
    )


TEAM_NOT_AGREED_SHIP = "opening merge requests changes the team's GitLab or GitHub, which needs full use"
NOT_AGREED = [
    "In individual use, agents change nothing the team sees:",
    "- the team's AI instructions: CLAUDE.md, AGENTS.md, .claude/",
    "- the team's own docs in the repo: its glossary, ADRs and coding standards",
    "- the team's GitHub or GitLab project, which is read-only for agents",
    "Agents still help you write code; you commit and push it as usual.",
]


def ask_team(repos: list[pathlib.Path], flag: str | None, planning_flag: str | None) -> str:
    """How should LETS work in these repos? Returns lets.kind: own (full use) or other (individual use). `flag` is
    --use (individual or full) or the older --team-agreed (yes or no). Without a terminal, an older script's --planning
    keeps its old meaning (private: individual; in-repo or team: full)."""
    if flag is not None:
        if flag not in ("yes", "no", "full", "individual"):
            raise LetsError("--use takes individual or full.")
        return "own" if flag in ("yes", "full") else "other"
    current = {git_config("lets.kind", r) for r in repos} - {""}
    by_flag = {"private": "other", "in-repo": "own", "team": "own"}.get(planning_flag or "")
    guess = by_flag or (current.pop() if len(current) == 1 else "other")
    if not ui.interactive():
        return guess
    label = repos[0].name if len(repos) == 1 else "these repos"
    pick = ui.select(
        "How should LETS work in %s?" % label,
        [
            (
                "individual",
                "Individual use",
                "agents read the code, docs, issues and merge requests and help you write code, but change nothing "
                "the team sees",
            ),
            (
                "full",
                "Full use",
                "your own repo, or the team has agreed: agents can also update its AI instructions, docs, issues and "
                "merge requests, within your other settings",
            ),
        ],
        "full" if guess == "own" else "individual",
        "Both choices assume you're allowed to use AI agents on this code.\n"
        "Agents never merge, approve or push to a shared branch, whichever you choose.",
    )
    if pick == "individual":
        for line in NOT_AGREED:
            ui.note(line)
    return "own" if pick == "full" else "other"


def upgrade_setup(repos: list[pathlib.Path], a: argparse.Namespace, screen) -> None:
    """Bring repos set up by an older LETS up to date: ask only what's new since then, keep every other answer, and
    take out what this version no longer creates."""
    screen("LETS setup", "what's new")
    for r in repos:
        ui.note("%s was set up by %s." % (r.name, set_up_by(r)))
    ui.out("LETS %s asks how LETS should work here; your other answers stay as they are." % SETUP_VERSION)
    kind = ask_team(repos, a.team_agreed, None)
    bases = {r.name: ask_base(r, a.base) for r in repos}
    changes = []
    for r in repos:
        agents = git_config("lets.agents", r)
        what = ["%s (git config; nothing committed)" % ("full use" if kind == "own" else "individual use")]
        if kind == "other" and agents == "ship":
            what.append("git: Commit instead of Ship (" + TEAM_NOT_AGREED_SHIP + ")")
        local = r / ".claude" / "settings.local.json"
        if "attribution" in json_of(local) or "includeCoAuthoredBy" in json_of(local):
            what.append("take LETS's old Claude Code settings out of .claude/settings.local.json")

        def apply(r: pathlib.Path = r, agents: str = agents) -> None:
            git("config", "lets.kind", kind, cwd=r)
            git("config", "lets.version", SETUP_VERSION, cwd=r)
            if kind == "other" and agents == "ship":
                git("config", "lets.agents", "commit", cwd=r)
            if bases.get(r.name):
                git("config", "lets.base", bases[r.name], cwd=r)
            remove_attribution_file(r)
            remember_repo(r)
            if kind == "other":
                exclude(r, ["CLAUDE.local.md"])

        changes.append(Change(r, "; ".join(what), apply=apply))
    agree(changes, "setup", a.yes, one_by_one=False)
    ui.out()
    ui.ok(
        "%s now up to date with LETS %s."
        % (", ".join(r.name for r in repos) + (" is" if len(repos) == 1 else " are"), SETUP_VERSION)
    )
    ui.note("To change any other answer, run `lets setup` again: it goes through every question.")


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
    if (
        all(git_config("lets.kind", r) for r in repos)
        and any(is_outdated(r) for r in repos)
        and not any((a.planning, a.url, a.plans_dir, a.build, a.tests, a.agents))
        and a.check is None
    ):
        upgrade_setup(repos, a, screen)
        return

    screen("LETS setup", "2 · how LETS works here, and plans")
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
    kind = ask_team(repos, a.team_agreed, a.planning)
    if not planning:
        current = was[repos[0].name][1] if mode == "one" else None
        opts = (
            [("in-repo", "In this repo", "in plans/, committed with the code")]
            if mode == "one" and kind == "own"
            else []
        ) + [
            ("team", "In a team planning repo", "a separate repo your teammates read and add to; work can link to it"),
            ("private", "In a private planning repo", "a separate repo only you see; nothing links to it"),
        ]
        keys = [o[0] for o in opts]
        default = (
            current if current in keys else ("private" if kind == "other" else ("in-repo" if mode == "one" else "team"))
        )
        planning = ui.select(
            "LETS keeps planning files: plans, specs and decisions. Where should the plans for %s live?"
            % (repos[0].name if len(repos) == 1 else "these repos"),
            opts,
            default,
        )
    if planning == "in-repo":
        if mode != "one":
            raise LetsError("Plans can live in the repo only when you set up one repo.")
        if kind != "own":
            raise LetsError(
                "Plans can live in the repo only with full use: committing "
                "them puts agent-made files in the team's repo. Choose a planning repo instead."
            )
        if foreign_plans(repos[0]):
            raise LetsError(
                "%s already has a plans/ folder that isn't LETS's. LETS keeps its plans there, so it won't "
                "mix with it: rename that folder, or choose a planning repo instead." % repos[0].name
            )
        others = agent_setup_in(repos[0])
        if "openspec/" in others and not uses_lets_here(repos[0]):
            raise LetsError(
                "%s already has its own openspec/ folder. Two sets of specs for the same code would leave nobody sure "
                "which is true, so LETS won't add plans/ here: choose a planning repo instead." % repos[0].name
            )
        if others and not uses_lets_here(repos[0]):
            ui.note(
                "Found the repo's own agent setup (%s). LETS leaves it untouched and adds only plans/."
                % ", ".join(others)
            )
    else:
        found = {r.name: agent_setup_in(r) for r in repos}
        found = {k: v for k, v in found.items() if v}
        if found:
            ui.note(
                "Found the repos' own agent setup (%s). LETS leaves it untouched."
                % "; ".join("%s: %s" % (k, ", ".join(v)) for k, v in found.items())
            )

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
    agents = choice_for_repo("git", a.agents, label, cur("lets.agents"), () if kind == "own" else ("ship",))
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
    changes = setup_changes(repos, planning, url, dest, build, tests, agents, checks, bases, credit, kind)
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
    """The branch work in this repo merges into: the flag (`auto` clears it), else what's set, else asked whenever
    there's a choice: another usual trunk (develop, trunk…) besides the remote's default branch, or several trunks and
    no default. None leaves it to detection (the remote's default branch)."""
    from .walkthrough import CANDIDATES

    if flag is not None:
        return None if flag in ("", "auto") else flag
    current = git_config("lets.base", r)
    if current:
        return current
    head = git("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", cwd=r, check=False)
    default = head.rsplit("/", 1)[-1] if head else ""
    trunks = [
        n
        for n in CANDIDATES
        if git("rev-parse", "--verify", "--quiet", n, cwd=r, check=False)
        or git("rev-parse", "--verify", "--quiet", "origin/" + n, cwd=r, check=False)
    ]
    if default and default in trunks:
        trunks.remove(default)
    choices = ([default] if default else []) + trunks
    if len(choices) < 2 or not ui.interactive():
        return None
    pick = ui.select(
        "Which branch does work in %s merge into?" % r.name,
        [(n, n, "the remote's default branch" if n == default else "") for n in choices],
        choices[0],
        "Reviews and walkthroughs compare your work with this branch.",
    )
    return None if pick == default else pick


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
    kind: str | None = None,
) -> list[Change]:
    """Everything setup would change, as Changes (made only once agreed)."""
    changes: list[Change] = []
    if planning != "in-repo":
        assert dest is not None

        def make_planning_repo(dest: pathlib.Path = dest, url: str | None = url, sharing: str = planning) -> None:
            from .planning import is_lets_file

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

            def changed(paths: list[str]) -> set[str]:
                if not (dest / ".git").exists():
                    return set()
                out = git("ls-files", "-m", "-o", "--exclude-standard", "--", *paths, cwd=dest, check=False) or ""
                return {line for line in out.splitlines() if line.strip()}

            mine = ["openspec", "repos.json", "README.md"]
            before = changed(mine)  # someone's own uncommitted work here stays out of the commit
            init_planning(dest)
            group = members(dest)
            for r in repos:
                group[r.name] = {"remote": git("remote", "get-url", "origin", cwd=r, check=False) or ""}
                git("config", "letsrepo.%s.path" % r.name, str(r), cwd=dest)
            (dest / "repos.json").write_text(json.dumps({"repos": group}, indent=2, sort_keys=True) + "\n")
            if is_lets_file(dest / "README.md", "kept by LETS (`lets setup`)"):
                (dest / "README.md").write_text(PLANNING_README.format(names=", ".join(sorted(group))))
            exclude(dest, [".lets/"])
            ours = sorted(changed(mine) - before)
            if ours:
                if not git("rev-parse", "--verify", "--quiet", "HEAD", cwd=dest, check=False):
                    git("checkout", "-q", "-B", "main", cwd=dest, check=False)
                git("add", "--", *ours, cwd=dest)
                msg = "lets setup: plans for %s" % ", ".join(sorted(group))
                run(["git", "commit", "-q", "--no-verify", "-m", msg, "--only", "--", *ours], cwd=dest)

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
                details="%s; only LETS's own files (openspec/config.yaml, repos.json, a README.md if there isn't one), "
                "committed locally (not pushed); anything else in the repo stays as it is" % (url or "existing repo"),
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
        changes += folder_changes([str(dest)], "the planning repo %s (only that folder)" % short_path(dest))
    for r in repos:

        def configure(r: pathlib.Path = r) -> None:
            values = {
                "lets.kind": kind or ("other" if planning == "private" else "own"),
                "lets.version": SETUP_VERSION,
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
            remove_attribution_file(r)
            remember_repo(r)
            if (kind or ("other" if planning == "private" else "own")) == "other":
                exclude(r, ["CLAUDE.local.md"])
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
