"""`lets doctor`: checks LETS is wired up on this computer, fixes what it can (shown and agreed first), and says
exactly what to do about the rest."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
from dataclasses import dataclass

from .changes import agree, is_ours, json_of, read
from .core import LetsError, say
from .install import GUARD_ENTRY, SESSION_ENTRY, codex_map_text, install_changes
from .paths import (
    PLUGIN,
    ROOT,
    P,
    codex_cli,
    codex_plugin_root,
    has_claude,
    has_codex,
    short_path,
    uses_claude,
    uses_codex,
    version,
)

TROUBLE = "~/lets/docs/troubleshooting.md"


@dataclass
class Problem:
    text: str
    fixable: bool  # `lets install`'s changes put it right
    how: str = ""  # for the rest: what to do (a troubleshooting section)


def plugin_files(root) -> dict[str, bytes]:
    out = {}
    for dp, _dn, fns in os.walk(str(root)):
        for fn in fns:
            p = os.path.join(dp, fn)
            out[os.path.relpath(p, str(root))] = pathlib.Path(p).read_bytes()
    return out


def problems() -> list[Problem]:
    out: list[Problem] = []
    if not (P.link.is_symlink() and os.path.realpath(str(P.link)) == str(ROOT.resolve())):
        out.append(Problem("~/lets doesn't point at this LETS (%s)" % ROOT, True))
    if not P.profile.exists():
        out.append(
            Problem(
                "no profile at %s" % short_path(P.profile), False, "run `lets install`: it asks the profile questions"
            )
        )
    if not shutil.which("python3"):
        out.append(
            Problem(
                "python3 isn't on PATH, so the guard can't run: git, gh and glab are blocked for agents",
                False,
                "install Python 3.11 or newer (%s#python)" % TROUBLE,
            )
        )
    hooks = (
        json.loads((PLUGIN / "hooks" / "hooks.json").read_text()) if (PLUGIN / "hooks" / "hooks.json").exists() else {}
    )
    if GUARD_ENTRY not in hooks.get("hooks", {}).get("PreToolUse", []):
        out.append(Problem("the plugin's guard hook is missing", False, "reinstall: npm install -g @nasiq/lets"))
    if uses_claude():
        if not is_ours(P.claude_plugin):
            out.append(Problem("Claude Code doesn't have the LETS commands (%s)" % short_path(P.claude_plugin), True))
        cm = read(P.claude_md)
        if "@~/lets/AGENTS.md" not in cm or "@%s" % P.profile not in cm:
            out.append(Problem("%s doesn't load the map and your profile" % short_path(P.claude_md), True))
        if shutil.which("claude"):
            listed = subprocess.run(
                ["claude", "plugin", "list"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            ).stdout
            if "lets@skills-dir" not in listed:
                out.append(
                    Problem(
                        "Claude Code doesn't list lets@skills-dir",
                        False,
                        "update Claude Code, then `lets install` (%s#claude-code)" % TROUBLE,
                    )
                )
    if uses_codex():
        groups = json_of(P.codex_hooks).get("hooks", {})
        if GUARD_ENTRY not in groups.get("PreToolUse", []) or SESSION_ENTRY not in groups.get("SessionStart", []):
            out.append(Problem("LETS's hooks are missing or changed in %s" % short_path(P.codex_hooks), True))
        if codex_map_text().rstrip() not in read(P.codex_agents):
            out.append(Problem("%s doesn't hold the current map and profile" % short_path(P.codex_agents), True))
        if "project_doc_fallback_filenames" not in read(P.codex_config):
            out.append(Problem("Codex isn't set to read CLAUDE.md-only repos", True))
        cp = codex_plugin_root()
        if cp is not None:
            if plugin_files(cp) != plugin_files(PLUGIN):
                out.append(
                    Problem(
                        "Codex's copy of the plugin is out of date",
                        False,
                        "run `codex plugin add lets@lets`, or `lets install` again",
                    )
                )
        elif codex_cli():
            out.append(
                Problem(
                    "the Codex plugin isn't installed",
                    False,
                    "run `codex plugin marketplace add ~/lets && codex plugin add lets@lets`",
                )
            )
    probe = subprocess.run(
        [sys.executable, str(ROOT / "agent-hooks" / "guard.py")],
        input=json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "git commit --no-verify -m probe"}, "cwd": str(P.home)}
        ),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if probe.returncode != 2:
        out.append(
            Problem(
                "the guard didn't block a --no-verify commit in a self-test (exit %d: %s)"
                % (probe.returncode, probe.stderr.strip()[-200:]),
                False,
                "report it: %s#guard" % TROUBLE,
            )
        )
    return out


def cmd_doctor(a) -> None:
    found = problems()
    say("LETS %s at %s" % (version(), ROOT))
    for name, found_it, used in (("Claude Code", has_claude(), uses_claude()), ("Codex", has_codex(), uses_codex())):
        if found_it:
            say("  %s: %s" % (name, "set up" if used else "not set up (your choice; `lets profile tools` to change)"))
    from .upgrade import SETUP_VERSION, describe, outdated_repos

    for r in outdated_repos():
        say(
            "  set up before LETS %s: %s. Run `lets setup` there: it asks only what's new."
            % (SETUP_VERSION, describe(r))
        )
    from .guardlog import doctor_lines

    for line in doctor_lines():
        say(line)
    if not found:
        say("Doctor: all checks pass.")
        return
    for p in found:
        say("  problem: " + p.text)
    if any(p.fixable for p in found):
        agree(install_changes(None), "doctor", a.yes, a.dry_run)
    left = problems() if not a.dry_run else found
    if not left:
        say("Doctor: fixed; all checks pass.")
        return
    for p in left:
        say("  still: %s%s" % (p.text, (" → " + p.how) if p.how else ""))
    raise LetsError("Some checks still fail; %s has more on each." % TROUBLE)
