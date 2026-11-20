"""lets: LETS's own command. Sets up your computer and repos for LETS, and reports on them.

The work itself happens in Claude Code or Codex, through the /lets: commands.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import sys
import traceback

from . import changes, ui
from .core import LetsError, git, git_config, say
from .paths import ISSUES, P, short_path, version

HELP_END = (
    """Start: `lets install`, then `lets setup` in a repo. Docs: ~/lets/docs. Problems: `lets doctor`, then
%s"""
    % ISSUES
)
QUIET = {"statusline", "session-start", "note"}  # run by tools many times a day: no update notice


def cmd_note(a: argparse.Namespace) -> None:
    """Notes LETS keeps about the branch you're on (local git config): which change or patch it is for, the mode it's
    being built in, and whether it was reviewed. The status line and the building commands read them."""
    branch = git("symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if not branch:
        raise LetsError("You're not on a branch.")
    key = "branch.%s." % branch
    if a.what in ("change", "patch"):
        if not a.name:
            raise LetsError("Which %s? `lets note %s <name>`." % (a.what, a.what))
        other = "patch" if a.what == "change" else "change"
        git("config", "--unset", key + "lets-" + other, check=False)
        git("config", key + "lets-" + a.what, a.name)
        if a.mode:
            git("config", key + "lets-mode", a.mode)
        if a.what == "change":
            remember_branch(a.name, branch)
        say("%s is for the %s %s%s." % (branch, a.what, a.name, " (%s)" % a.mode if a.mode else ""))
    elif a.what == "base":
        if not a.name:
            raise LetsError("Which branch does this one merge into? `lets note base <branch>` (`auto` to detect it).")
        if a.name == "auto":
            git("config", "--unset", key + "lets-base", check=False)
            say("%s's base is detected again." % branch)
        else:
            git("config", key + "lets-base", a.name)
            say("%s merges into %s: walkthroughs and checks compare against it." % (branch, a.name))
    elif a.what == "examples":
        if a.name not in ("real", "made-up"):
            raise LetsError("`lets note examples real` or `lets note examples made-up`.")
        git("config", "lets.note-examples", a.name)
        say("Learning notes made in this repo use %s examples." % a.name)
    elif a.what == "reviewed":
        git("config", key + "lets-reviewed", git("rev-parse", "HEAD"))
        say("Recorded: %s reviewed at %s." % (branch, git("rev-parse", "--short", "HEAD")))
    else:
        for k in ("change", "patch", "mode", "base", "reviewed", "walked"):
            v = git_config(key + "lets-" + k)
            if v:
                say("%s: %s" % (k, v))


def remember_branch(change: str, branch: str) -> None:
    """Record the branch on the change itself (`x-lets-branch`), so its pull request can still be found after the
    branch is merged and deleted."""
    from .planning import planning_root
    from .work import label, set_label

    proot, _ = planning_root(pathlib.Path.cwd())
    folder = proot / "openspec" / "changes" / change if proot else None
    if folder and folder.is_dir() and not label(folder, "x-lets-branch"):
        set_label(folder, "x-lets-branch", branch)


def parser() -> argparse.ArgumentParser:
    from .checks import cmd_check, cmd_walkthrough
    from .doctor import cmd_doctor
    from .guardlog import cmd_guard_log
    from .install import cmd_install, cmd_uninstall, cmd_update
    from .planning import cmd_sync, cmd_where
    from .profile import CHOICES, cmd_profile
    from .setup import cmd_setup
    from .statusline import cmd_statusline

    p = argparse.ArgumentParser(
        prog="lets",
        description=(__doc__ or "").splitlines()[0],
        epilog=HELP_END,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version="LETS %s" % version())
    sub = p.add_subparsers(dest="cmd", metavar="<command>")

    s = sub.add_parser("install", help="set LETS up on this computer for Claude Code and Codex (re-run any time)")
    s.add_argument("--dry-run", action="store_true", help="show what would change, change nothing")
    s.add_argument("--yes", action="store_true", help="make the changes without asking (for scripts)")
    s.add_argument("--force", action="store_true", help="point ~/lets at this LETS even if it points elsewhere")
    s.add_argument("--tools", help="which tools to set up when both are installed: claude, codex or claude,codex")
    s.set_defaults(fn=cmd_install)

    s = sub.add_parser("setup", help="set up a repo, or several related repos (guided; flags answer its questions)")
    s.add_argument("--mode", choices=["one", "group"], help="one repo, or several related repos")
    s.add_argument("--path", help="the repo, or (with --mode group) the folder holding the repos")
    s.add_argument("--repos", help="with --mode group: which repos, comma-separated")
    s.add_argument("--planning", choices=["in-repo", "team", "private"], help="where the plans live")
    s.add_argument("--url", help="the planning repo's clone URL (team or private)")
    s.add_argument("--plans-dir", help="where planning repos are kept on this computer")
    for c, flag in ((CHOICES[0], "--build"), (CHOICES[1], "--tests"), (CHOICES[2], "--agents")):
        s.add_argument(
            flag,
            choices=[o.key for o in c.options],
            help="%s (default: your profile)" % c.heading.split(" (")[0].lower(),
        )
    s.add_argument("--check", help="the repo's quick check, e.g. 'npm run -s check' ('' for none)")
    s.add_argument("--base", help="the branch work here merges into, e.g. develop ('auto' to detect it)")
    s.add_argument(
        "--use",
        dest="team_agreed",
        choices=["individual", "full"],
        help="how LETS works here: individual (agents change nothing the team sees) or full (your own repo, or the "
        "team has agreed)",
    )
    s.add_argument("--team-agreed", dest="team_agreed", choices=["yes", "no"], help=argparse.SUPPRESS)
    s.add_argument(
        "--ai-credit",
        help="AI credit here: never, trailer, trailer-pr (or trailer:'<line>'), or profile to follow your profile",
    )
    s.add_argument("--yes", action="store_true", help="make the changes without asking (for scripts)")
    s.add_argument("--remove", action="store_true", help="clear this repo's LETS settings (its plans stay)")
    s.set_defaults(fn=cmd_setup)

    s = sub.add_parser("profile", help="change an answer in your profile (how you like to work)")
    s.add_argument("question", nargs="?", help="go straight to one question (a prefix is enough)")
    s.set_defaults(fn=cmd_profile)

    sub.add_parser("where", help="print where this repo's plans live, and its choices").set_defaults(fn=cmd_where)
    sub.add_parser("sync", help="bring a team planning repo up to date (fast-forward only)").set_defaults(fn=cmd_sync)

    s = sub.add_parser("check", help="list weakened gates (skipped tests, loosened checks) in this branch's changes")
    s.add_argument("--run", action="store_true", help="then run the repo's quick check")
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("walkthrough", help="scope | complete | status: the files a walkthrough covers")
    s.add_argument("action", choices=["scope", "complete", "status"])
    s.set_defaults(fn=cmd_walkthrough)

    s = sub.add_parser("note", help="what this branch is for (the building commands record it)")
    s.add_argument(
        "what", nargs="?", choices=["change", "patch", "base", "reviewed", "examples", "show"], default="show"
    )
    s.add_argument("name", nargs="?")
    s.add_argument("--mode", choices=["pair", "agent"])
    s.set_defaults(fn=cmd_note)

    s = sub.add_parser("changes", help="where each change stands: tasks, branch, and its pull request (read only)")
    s.add_argument("change", nargs="?")
    s.add_argument("--json", action="store_true", help="for agents")
    s.add_argument("--offline", action="store_true", help="local files only; don't read GitLab or GitHub")
    s.set_defaults(fn=lambda a: __import__("lets.work", fromlist=["cmd_changes"]).cmd_changes(a))

    s = sub.add_parser("doctor", help="check LETS is wired up on this computer, and fix what it can")
    s.add_argument("--dry-run", action="store_true", help="show the fixes, make none")
    s.add_argument("--yes", action="store_true", help="make the fixes without asking")
    s.set_defaults(fn=cmd_doctor)

    s = sub.add_parser("guard", help="log: what the guard blocked, asked about or crashed on lately")
    s.add_argument("action", choices=["log"])
    s.add_argument("--last", type=int, help="how many entries to show (default 20)")
    s.set_defaults(fn=cmd_guard_log)

    s = sub.add_parser("update", help="show what a newer LETS changes, then install it")
    s.add_argument("--yes", action="store_true", help="update without asking")
    s.set_defaults(fn=cmd_update)

    s = sub.add_parser("uninstall", help="take LETS out of Claude Code and Codex (your profile and plans stay)")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_uninstall)

    s = sub.add_parser(
        "statusline", help="on | off: LETS's status line in Claude Code (alone: print it, for Claude Code)"
    )
    s.add_argument("action", nargs="?", choices=["on", "off"])
    s.add_argument("--dry-run", action="store_true", help="show the change, make none")
    s.add_argument("--yes", action="store_true", help="make the change without asking")
    s.set_defaults(fn=cmd_statusline)
    return p


def log_crash(exc: BaseException) -> str:
    P.logs.mkdir(parents=True, exist_ok=True)
    f = P.logs / ("%s.log" % datetime.date.today().isoformat())
    with f.open("a") as out:
        out.write(
            "\n%s lets %s (LETS %s)\n"
            % (datetime.datetime.now().isoformat(timespec="seconds"), " ".join(sys.argv[1:]), version())
        )
        out.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    return short_path(f)


def made_so_far() -> None:
    if changes.MADE:
        ui.out("Already changed:")
        for m in changes.MADE:
            ui.out("  " + m)
        ui.out("Re-run the same command to carry on: it picks up where this stopped.")
    else:
        ui.out("Nothing was changed.")


def main(argv: list[str] | None = None) -> None:
    if os.name == "nt":
        raise SystemExit("LETS runs on Linux and macOS. On Windows, use it inside WSL (Windows Subsystem for Linux).")
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["session-start"]:  # run by the session-start hook; not a command people type
        from .session import cmd_session_start

        try:
            cmd_session_start()
        except Exception:  # noqa: BLE001  never break a session over a notice
            pass
        return
    p = parser()
    a = p.parse_args(argv)
    if not getattr(a, "fn", None):
        p.print_help()
        raise SystemExit(2)
    try:
        a.fn(a)
    except LetsError as e:
        sys.stderr.write("%s\n" % e)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        ui.out()
        ui.out("Cancelled.")
        made_so_far()
        raise SystemExit(130) from None
    except Exception as e:  # noqa: BLE001
        where = log_crash(e)
        sys.stderr.write(
            "LETS hit an unexpected error: %s: %s\nThe details are in %s.\n" % (type(e).__name__, e, where)
        )
        made_so_far()
        sys.stderr.write("Please report it, with that file: %s\n" % ISSUES)
        raise SystemExit(1) from None
    if a.cmd not in QUIET and sys.stdout.isatty():
        from .session import notice

        n = notice()
        if n:
            ui.note(n)
