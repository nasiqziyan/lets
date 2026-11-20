"""`lets install`, `lets uninstall` and `lets update`: wiring LETS into Claude Code and Codex on this computer."""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from . import profile, settings, ui
from .changes import Change, agree, block_text, is_ours, json_of, link_change, read, without_block
from .core import LetsError, git, run
from .paths import (
    MARKETPLACE,
    PACKAGE,
    ROOT,
    P,
    chosen_tools,
    codex_cli,
    has_claude,
    has_codex,
    short_path,
    uses_claude,
    uses_codex,
    version,
)

GUARD = 'sh "$HOME/lets/agent-hooks/guard.sh"'
SESSION = 'sh "$HOME/lets/agent-hooks/session-start.sh"'
GUARD_MATCHER = "Bash|Edit|Write|MultiEdit|NotebookEdit|apply_patch"  # shell and file-edit tools in both tools
GUARD_ENTRY = {"matcher": GUARD_MATCHER, "hooks": [{"type": "command", "command": GUARD, "timeout": 600}]}
SESSION_ENTRY = {"hooks": [{"type": "command", "command": SESSION, "timeout": 30}]}
STATUSLINE = {"type": "command", "command": "~/lets/bin/lets statusline", "padding": 0, "refreshInterval": 5}
NO_ATTRIBUTION = {"commit": "", "pr": ""}
CODEX_ROOTS_TAG = "# lets: learning notes and planning repos"
CODEX_FALLBACK_TAG = "# lets: read CLAUDE.md-only repos"


def ours(entry: dict) -> bool:
    return any("lets/agent-hooks/" in h.get("command", "") for h in entry.get("hooks", []))


def hooks_text(text: str, add: bool = True) -> str:
    """A hooks.json (Codex) with LETS's guard and session-start entries added, or taken out."""
    data = json.loads(text) if text.strip() else {}
    hooks = data.setdefault("hooks", {})
    for event, entry in (("PreToolUse", GUARD_ENTRY), ("SessionStart", SESSION_ENTRY)):
        kept = [g for g in hooks.get(event, []) if not ours(g)]
        hooks[event] = kept + ([json.loads(json.dumps(entry))] if add else [])
        if not hooks[event]:
            del hooks[event]
    return json.dumps(data, indent=2) + "\n"


LEDGER = "host-settings.json"  # in LETS's state folder: what LETS changed in each tool's settings, to undo exactly
ABSENT = "<absent>"
UNKNOWN = "<unknown>"


def ledger() -> dict:
    return json_of(P.state / LEDGER)


def save_ledger(data: dict) -> None:
    P.state.mkdir(parents=True, exist_ok=True)
    (P.state / LEDGER).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def note_claude_priors(text: str, dirs: list[str]) -> None:
    """Before LETS first writes a Claude Code setting, remember what was there, so uninstall can put it back. A value
    already equal to LETS's with no record means an older LETS wrote it: unknown, so uninstall leaves it."""
    data = json.loads(text) if text.strip() else {}
    led = ledger()
    claude = led.setdefault("claude", {})
    wrote = {"attribution": dict(NO_ATTRIBUTION), "includeCoAuthoredBy": False}
    for key, value in wrote.items():
        if key in claude:
            continue
        if key not in data:
            prior = ABSENT
        elif data[key] == value and not led.get("since"):
            prior = UNKNOWN
        else:
            prior = data[key]
        claude[key] = {"prior": prior, "wrote": value}
    allowed = data.get("permissions", {}).get("additionalDirectories", [])
    added = claude.setdefault("added_dirs", [])
    added += [d for d in dirs if d not in allowed and d not in added]
    led.setdefault("since", "recorded")
    save_ledger(led)


def broad_planning_grants(allowed: list[str]) -> list[str]:
    """Folders an older LETS granted for planning repos (the folder they sit in, siblings and all): only those it
    recorded adding, or, with no record, the planning folders themselves."""
    added = ledger().get("claude", {}).get("added_dirs")
    parents = [str(d) for d in settings.plans_dirs()]
    planning = {str(p) for p in planning_repos_known().values()}
    return [d for d in allowed if d in parents and d not in planning and (added is None or d in added)]


def claude_settings_text(text: str, dirs: list[str], statusline: bool | None, drop: tuple[str, ...] = ()) -> str:
    """Claude Code's settings with LETS's parts: no AI attribution, the folders LETS writes to, and (if chosen) the
    status line. `drop`: folders LETS granted before that are wider than it needs."""
    data = json.loads(text) if text.strip() else {}
    data["attribution"] = dict(NO_ATTRIBUTION)
    data["includeCoAuthoredBy"] = False
    allowed = data.setdefault("permissions", {}).setdefault("additionalDirectories", [])
    allowed[:] = [d for d in allowed if d not in drop]
    for d in dirs:
        if d not in allowed:
            allowed.append(d)
    if statusline:
        data["statusLine"] = dict(STATUSLINE)
    return json.dumps(data, indent=2) + "\n"


def codex_config_text(text: str, roots: list[str]) -> str:
    """Codex's config.toml with LETS's two settings: read CLAUDE.md-only repos, and write to LETS's folders."""
    text = "".join(line for line in text.splitlines(True) if CODEX_ROOTS_TAG not in line)
    if not re.search(r"^\s*project_doc_fallback_filenames\s*=", text, re.M):
        line = 'project_doc_fallback_filenames = ["CLAUDE.md"]  %s\n' % CODEX_FALLBACK_TAG
        table = re.search(r"^\s*\[", text, re.M)
        text = (
            text[: table.start()] + line + text[table.start() :]
            if table
            else text + ("\n" if text and not text.endswith("\n") else "") + line
        )
    if roots:
        line = "writable_roots = [%s]  %s\n" % (", ".join('"%s"' % r for r in roots), CODEX_ROOTS_TAG)
        table = re.search(r"^\s*\[sandbox_workspace_write\]\s*$", text, re.M)
        text = (
            (text[: table.end() + 1] + line + text[table.end() + 1 :])
            if table
            else text + ("\n" if text and not text.endswith("\n") else "") + "\n[sandbox_workspace_write]\n" + line
        )
    return text


def codex_roots(text: str) -> list[str]:
    m = re.search(r"^writable_roots = \[(.*)\]\s*" + re.escape(CODEX_ROOTS_TAG), text, re.M)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def lets_dirs() -> list[str]:
    """The folders agents may write to outside the repo: learning notes, your additions (`/lets:add`) and each planning
    repo itself (never the folder it sits in, which may hold code repos too)."""
    notes = settings.notes_dir()
    return (
        ([str(notes)] if notes else []) + [str(P.additions)] + sorted(str(p) for p in planning_repos_known().values())
    )


def planning_repos_known() -> dict[str, pathlib.Path]:
    from .planning import planning_repos_known as known

    return known()


def folder_changes(dirs: list[str], label: str) -> list[Change]:
    """Let both tools write to LETS's folders."""
    out = []
    if uses_claude():
        cs = P.claude_settings
        data = json_of(cs)
        missing = [d for d in dirs if d not in data.get("permissions", {}).get("additionalDirectories", [])]
        if missing:

            def add(old: str, m: list[str] = missing) -> str:
                led = ledger()
                added = led.setdefault("claude", {}).setdefault("added_dirs", [])
                added += [d for d in m if d not in added]
                save_ledger(led)
                return _add_dirs(old, m)

            out.append(Change(cs, "let Claude Code write %s" % label, edit=add))
    if uses_codex():
        cfg = P.codex_config
        text = read(cfg)
        if re.search(r"^\s*writable_roots\s*=", text, re.M) and CODEX_ROOTS_TAG not in text:
            missing = [d for d in dirs if d not in text]
            if missing:
                out.append(
                    Change(
                        cfg,
                        "Codex: add %s to your own writable_roots yourself" % ", ".join(missing),
                        details="Your config.toml already sets writable_roots, so LETS won't edit it. Add: "
                        + ", ".join('"%s"' % d for d in missing),
                    )
                )
        else:

            def edit(old: str, want: tuple[str, ...] = tuple(dirs)) -> str:
                broad = {str(d) for d in settings.plans_dirs()} - set(want)
                return codex_config_text(old, sorted(set(want) | (set(codex_roots(old)) - broad)))

            if edit(text) != text:
                out.append(
                    Change(
                        cfg,
                        "let Codex write %s%s"
                        % (
                            label,
                            "" if "project_doc_fallback_filenames" in text else ", and read CLAUDE.md-only repos",
                        ),
                        edit=edit,
                    )
                )
    return out


def _add_dirs(text: str, dirs: list[str]) -> str:
    data = json.loads(text) if text.strip() else {}
    allowed = data.setdefault("permissions", {}).setdefault("additionalDirectories", [])
    allowed += [d for d in dirs if d not in allowed]
    return json.dumps(data, indent=2) + "\n"


def codex_map_text() -> str:
    """What Codex reads globally: the map, then the profile (Codex has no imports)."""
    text = (ROOT / "AGENTS.md").read_text().rstrip() + "\n"
    if P.profile.exists():
        text += "\n" + P.profile.read_text().rstrip() + "\n"
    return text


def refresh_codex_copy() -> None:
    """After the profile changes: Codex keeps its own copy of the map and profile, so refresh it."""
    if uses_codex() and P.codex_agents.exists():
        new = block_text(P.codex_agents, codex_map_text())
        if new != read(P.codex_agents):
            Change(P.codex_agents, "refresh LETS's map and your profile", new).apply()


def openspec_bundled() -> pathlib.Path:
    return ROOT / "node_modules" / ".bin" / "openspec"


def openspec_wanted() -> str:
    deps = json.loads((ROOT / "package.json").read_text()).get("dependencies", {})
    return deps.get("@fission-ai/openspec", "").lstrip("^~=")


def openspec_bin() -> str:
    """The OpenSpec LETS runs: the one it ships with, or the one on PATH."""
    return str(openspec_bundled()) if openspec_bundled().exists() else (shutil.which("openspec") or "openspec")


def install_changes(statusline: bool | None) -> list[Change]:
    """Everything install would change outside LETS's package, safest first. Nothing is written here."""
    changes: list[Change | None] = []
    if not (P.link.exists() or P.link.is_symlink()):
        changes.append(
            Change(
                P.link,
                "link ~/lets to LETS (every file below points through it)",
                apply=lambda: P.link.symlink_to(ROOT),
                details="a link to %s" % ROOT,
            )
        )
    if uses_claude():
        changes.append(
            link_change(
                P.claude_plugin, P.link / "plugin", "add the LETS commands to Claude Code (its guard comes with them)"
            )
        )
        new = block_text(P.claude_md, "@~/lets/AGENTS.md\n@%s" % P.profile)
        if new != read(P.claude_md):
            changes.append(Change(P.claude_md, "load LETS's map and your profile in every session", new))
        old = read(P.claude_settings)
        dirs = lets_dirs()
        current = (json.loads(old) if old.strip() else {}).get("permissions", {}).get("additionalDirectories", [])
        drop = tuple(broad_planning_grants(current))
        if claude_settings_text(old, dirs, statusline, drop) != old:
            note_claude_priors(old, dirs)
            what = ["no AI attribution in commits and pull requests", "let it write LETS's folders"] + (
                ["show LETS's progress in the status line"] if statusline else []
            )
            if drop:
                what.append("narrow %s to the planning repos inside it" % ", ".join(short_path(d) for d in drop))
            changes.append(
                Change(
                    P.claude_settings,
                    "; ".join(what),
                    edit=lambda t, d=dirs, s=statusline, x=drop: claude_settings_text(t, d, s, x),
                )
            )
    if uses_codex():
        new = block_text(P.codex_agents, codex_map_text())
        if new != read(P.codex_agents):
            changes.append(Change(P.codex_agents, "load LETS's map and your profile in every session", new))
        if hooks_text(read(P.codex_hooks)) != read(P.codex_hooks):
            changes.append(
                Change(P.codex_hooks, "add the LETS guard and its session-start check", edit=lambda t: hooks_text(t))
            )
        changes += [c for c in folder_changes(lets_dirs(), "LETS's folders") if c.path == P.codex_config]
    lets_on_path = shutil.which("lets")
    if not lets_on_path or os.path.realpath(lets_on_path) != os.path.realpath(str(ROOT / "bin" / "lets")):
        if not lets_on_path:
            changes.append(
                link_change(P.local_bin / "lets", P.link / "bin" / "lets", "let you type `lets` from anywhere")
            )
    if not shutil.which("openspec") and openspec_bundled().exists():
        changes.append(
            link_change(P.local_bin / "openspec", openspec_bundled(), "let agents run OpenSpec, which LETS ships with")
        )
    return [c for c in changes if c is not None]


def requirements() -> tuple[list[str], list[str], list[str]]:
    """(missing, notes, tools found) for install."""
    missing, notes = [], []
    if not shutil.which("git"):
        missing.append("git (Ubuntu: sudo apt install git; macOS: xcode-select --install)")
    want = openspec_wanted()
    other = shutil.which("openspec")
    if other and os.path.realpath(other) != os.path.realpath(str(openspec_bundled())):
        got = run(["openspec", "--version"], check=False).stdout.strip()
        if want and got != want:
            notes.append(
                "OpenSpec %s is on your PATH; LETS ships %s and agents will run yours. To match: "
                "npm install -g @fission-ai/openspec@%s" % (got, want, want)
            )
    elif not other and not openspec_bundled().exists():
        missing.append("OpenSpec %s: npm install -g @fission-ai/openspec@%s" % (want, want))
    tools = [n for n, ok in (("Claude Code", has_claude()), ("Codex", has_codex())) if ok]  # found, chosen or not
    if not tools:
        missing.append("Claude Code or Codex")
    return missing, notes, tools


def command_clash() -> str | None:
    """Another program called `lets` that comes before LETS on PATH (a task runner shares the name)."""
    found = shutil.which("lets")
    if found and os.path.realpath(found) != os.path.realpath(str(ROOT / "bin" / "lets")):
        return found
    return None


def preflight(force: bool) -> None:
    """Stop before changing anything if a file LETS would edit isn't safe to edit."""
    for f in (P.claude_settings, P.codex_hooks):
        if f.exists() and f.read_text().strip():
            try:
                json.loads(f.read_text())
            except ValueError as e:
                raise LetsError(
                    "%s isn't plain JSON (%s), so nothing was changed. Fix or move it, then re-run."
                    % (short_path(f), e)
                ) from None
    cd = P.claude_plugin
    if (cd.exists() or cd.is_symlink()) and not is_ours(cd):
        raise LetsError(
            "%s already exists and isn't LETS, so nothing was changed. Rename or move it, then re-run." % short_path(cd)
        )
    if (P.link.exists() or P.link.is_symlink()) and os.path.realpath(str(P.link)) != str(ROOT.resolve()):
        if not P.link.is_symlink():
            raise LetsError("~/lets exists and isn't a link to LETS, so nothing was changed. Move it, then re-run.")
        if not force:
            raise LetsError(
                "~/lets points at %s, another copy of LETS. Re-run with --force to point it at this one "
                "(%s)." % (os.path.realpath(str(P.link)), ROOT)
            )
        P.link.unlink()


def cmd_statusline_switch(a) -> None:
    """`lets statusline on|off`: put LETS's status line in Claude Code, or take it out. Yours is only replaced when you
    agree, and it's backed up first."""
    if not uses_claude():
        raise LetsError("Claude Code isn't set up on this computer, so there's no status line to change.")
    current = json_of(P.claude_settings).get("statusLine")
    if a.action == "on":
        if current == STATUSLINE:
            ui.out("LETS's status line is already on.")
            return

        def put(text: str) -> str:
            data = json.loads(text) if text.strip() else {}
            data["statusLine"] = dict(STATUSLINE)
            return json.dumps(data, indent=2) + "\n"

        summary = "show LETS's progress in the status line"
        if current:
            summary += " (replaces yours: %s)" % (current.get("command") or "your own")
        made = agree([Change(P.claude_settings, summary, edit=put)], "statusline on", a.yes, a.dry_run, False)
        if made and current:
            data = settings.load()
            data["your_statusline"] = current
            settings.save(data)
            ui.note(
                "Yours is saved: `lets statusline off` puts it back. To show both, call `lets statusline` from your "
                "own script and print what it prints."
            )
        return
    if current != STATUSLINE:
        ui.out("LETS's status line isn't on%s." % (": yours stays as it is" if current else ""))
        return

    saved = settings.load().get("your_statusline")

    def take(text: str) -> str:
        data = json.loads(text) if text.strip() else {}
        data.pop("statusLine", None)
        if saved:
            data["statusLine"] = saved
        return json.dumps(data, indent=2) + "\n"

    what = "take out LETS's status line" + (
        " and put yours back (%s)" % (saved.get("command") or "your own") if saved else ""
    )
    if agree([Change(P.claude_settings, what, edit=take)], "statusline off", a.yes, a.dry_run, False) and saved:
        data = settings.load()
        data.pop("your_statusline", None)
        settings.save(data)


def ask_statusline(yes: bool) -> bool | None:
    """Offer LETS's status line in Claude Code, only when you don't already have one."""
    if not uses_claude() or "statusLine" in json_of(P.claude_settings):
        return None
    if yes or not ui.interactive():
        return True
    ui.out()
    return ui.confirm(
        "Show LETS's progress in Claude Code's status line?",
        True,
        "Yes",
        "No",
        "One line: the epic, the change and the task you're on, with progress dots. For example:\n"
        "  shop-checkout ●◉○○ › take-card-payment ●●◉○ › Validate the card number   ✎ pair",
    )


def after_notes_moved(old: pathlib.Path | None, new: pathlib.Path | None) -> None:
    """After the notes folder changes: move the notes already saved (shown and agreed), and let the tools write to the
    new folder. The old folder stays in the tools' permissions until you remove it; it's harmless."""
    changes: list[Change] = []
    if old and new and old != new and old.is_dir():
        notes = sorted(f for f in old.glob("*.md") if not (new / f.name).exists())
        if notes:

            def move(notes: list[pathlib.Path] = notes, new: pathlib.Path = new) -> None:
                new.mkdir(parents=True, exist_ok=True)
                for f in notes:
                    shutil.move(str(f), str(new / f.name))

            changes.append(
                Change(
                    new,
                    "move your %d learning note%s here from %s"
                    % (len(notes), "" if len(notes) == 1 else "s", short_path(old)),
                    apply=move,
                    details="\n".join(f.name for f in notes),
                )
            )
    changes += install_changes(None)
    agree(changes, "profile notes", False, False, False)


TOOL_NAMES = {"claude": "Claude Code", "codex": "Codex"}


def ask_tools(flag: str | None, yes: bool) -> None:
    """Which tools LETS sets up: the --tools flag, else asked once when both are found (not asked again)."""
    if flag:
        want = [t.strip() for t in flag.split(",") if t.strip()]
        bad = [t for t in want if t not in TOOL_NAMES]
        if bad or not want:
            raise LetsError("--tools takes claude, codex or both (claude,codex).")
        save_tools(want)
        return
    if chosen_tools() is not None or not (has_claude() and has_codex()):
        return
    pick = "both"
    if ui.interactive() and not yes:
        ui.out()
        pick = ui.select(
            "Which tools should LETS set up?",
            [
                ("both", "Both", "Claude Code and Codex"),
                ("claude", "Claude Code only", ""),
                ("codex", "Codex only", ""),
            ],
            "both",
        )
    save_tools(["claude", "codex"] if pick == "both" else [pick])


def save_tools(tools: list[str]) -> None:
    data = settings.load()
    data["tools"] = tools
    settings.save(data)


def cmd_tools() -> None:
    """`lets profile tools`: change which tools LETS is set up in. A tool switched off has LETS taken out of it (as
    uninstall would, for that tool only); one switched on is set up. Shown and agreed first."""
    found = [t for t, ok in (("claude", has_claude()), ("codex", has_codex())) if ok]
    if len(found) < 2:
        raise LetsError(
            "Only %s is installed here, so there's nothing to choose."
            % (TOOL_NAMES[found[0]] if found else "no coding agent")
        )
    if not ui.interactive():
        raise LetsError("`lets profile tools` asks a question: run it in a terminal (or `lets install --tools ...`).")
    before = chosen_tools() or found
    pick = ui.select(
        "Which tools should LETS set up?",
        [("both", "Both", "Claude Code and Codex"), ("claude", "Claude Code only", ""), ("codex", "Codex only", "")],
        "both" if len(before) == 2 else before[0],
    )
    after = ["claude", "codex"] if pick == "both" else [pick]
    if sorted(after) == sorted(before):
        ui.ok("No change: LETS is set up in %s." % " and ".join(TOOL_NAMES[t] for t in after))
        return
    off = [t for t in before if t not in after]
    dirs = {"claude": P.claude, "codex": P.codex}
    removals = [c for c in uninstall_changes() if any(str(c.path).startswith(str(dirs[t]) + os.sep) for t in off)]
    save_tools(after)
    changes = removals + install_changes(None)
    made = agree(changes, "profile tools", False, False, False)
    if not made and changes:
        save_tools(before)
        return
    if "codex" in off and codex_cli():
        run([codex_cli(), "plugin", "remove", "lets@%s" % MARKETPLACE], check=False)
    if "codex" in after and "codex" not in before and codex_cli():
        run([codex_cli(), "plugin", "marketplace", "add", str(P.link)], check=False)
        run([codex_cli(), "plugin", "add", "lets@%s" % MARKETPLACE], check=False)
    ui.ok("LETS is now set up in %s." % " and ".join(TOOL_NAMES[t] for t in after))


def cmd_install(a) -> None:
    dry, yes = a.dry_run, a.yes
    preflight(a.force)
    missing, notes, tools = requirements()
    ui.title("LETS install", "this computer" + (" · dry run" if dry else ""))
    ui.ok("Found: " + ", ".join(tools) if tools else "No coding agent found")
    for n in notes:
        ui.warn(n)
    if missing:
        for m in missing:
            ui.warn("Missing: " + m)
        raise LetsError("Install what's missing, then run `lets install` again.")
    if not dry:
        ask_tools(getattr(a, "tools", None), yes)
    asked = profile.ensure(dry)
    if dry and asked:
        ui.note(asked)
    statusline = None if dry else ask_statusline(yes)
    made = agree(install_changes(statusline), "install", yes, dry)
    if dry:
        return
    if uses_codex() and codex_cli():
        r1 = run([codex_cli(), "plugin", "marketplace", "add", str(P.link)], check=False)
        r2 = run([codex_cli(), "plugin", "add", "lets@%s" % MARKETPLACE], check=False)
        if r2.returncode != 0:
            ui.warn(
                "Codex plugin: run `codex plugin marketplace add ~/lets && codex plugin add lets@lets` (%s)"
                % (r2.stdout + r2.stderr + r1.stderr).strip()[-200:]
            )
    trust_hooks = uses_codex() and any(c.path == P.codex_hooks for c in made)
    run(
        [openspec_bin(), "config", "set", "telemetry.enabled", "false"],
        check=False,
        env=dict(os.environ, OPENSPEC_TELEMETRY="0"),
    )
    data = settings.load()
    data["installed"] = version()
    settings.save(data)
    from .doctor import problems

    errors = [p.text for p in problems()]
    ui.out()
    for e in errors:
        ui.warn(e)
    if not errors:
        ui.ok("LETS %s is installed, and its checks pass." % version())
    clash = command_clash()
    if clash:
        ui.warn(
            "Another program called `lets` comes first on your PATH (%s), so typing `lets` runs it. Use "
            "~/lets/bin/lets, or put %s earlier in your PATH." % (clash, short_path(P.local_bin))
        )
    elif str(P.local_bin) not in os.environ.get("PATH", "").split(os.pathsep) and not shutil.which("lets"):
        ui.note("Add ~/.local/bin to your PATH to type `lets` instead of ~/lets/bin/lets.")
    if profile.answer("updates") == "on":
        ui.note("LETS checks for a new version at most once a day (`lets profile updates` turns it off).")
    from .upgrade import SETUP_VERSION, describe, outdated_repos

    old = outdated_repos()
    here = git("rev-parse", "--show-toplevel", cwd=os.getcwd(), check=False)
    steps = []
    if errors:
        steps.append("Fix what failed: run `lets doctor`.")
    if trust_hooks:
        steps.append(
            "Codex: open Codex once, type /hooks and trust LETS's hooks. Until you do, Codex won't run the guard."
        )
    if old:
        steps.append(
            "Set up before LETS %s: %s. Run `lets setup` in each: it asks only what's new and keeps your other "
            "answers." % (SETUP_VERSION, ", ".join(describe(r) for r in old))
        )
    offer = not errors and here and not git("config", "--get", "lets.kind", cwd=here, check=False) and ui.interactive()
    if not offer:
        steps.append(
            "Run `lets setup` in %s when you're ready."
            % ("this repo" if here else "a repo you work in, or in a folder of related repos,")
            if not old
            else "To set up another repo, run `lets setup` in it."
        )
    if steps:
        ui.out()
        ui.out(ui.paint("Next:", "bold"))
        for n, s_ in enumerate(steps, 1):
            ui.out("  %d. %s" % (n, s_))
    if errors:
        raise LetsError("LETS is installed, but the checks above failed: `lets doctor` can fix most of them.")
    if offer and ui.confirm("Do you want to set up this repo (%s) now?" % os.path.basename(here), True):
        from .setup import cmd_setup, setup_args

        cmd_setup(setup_args())


# ---------- uninstall ----------


def uninstall_changes() -> list[Change]:
    out: list[Change] = []
    for p in (P.claude_plugin, P.local_bin / "lets", P.local_bin / "openspec"):
        if is_ours(p):
            out.append(Change(p, "remove LETS's link", apply=p.unlink))
    for path in (P.claude_md, P.codex_agents):
        if path.exists() and without_block(read(path)) != read(path):
            out.append(Change(path, "take out LETS's map and your profile", edit=without_block))
    if P.claude_settings.exists():
        claude = ledger().get("claude", {})
        kept = []

        def undo_claude(text: str) -> str:
            data = json.loads(text) if text.strip() else {}
            allowed = data.get("permissions", {}).get("additionalDirectories", [])
            ours = claude.get("added_dirs")
            ours = set(ours) if ours is not None else set(lets_dirs()) | {str(d) for d in settings.plans_dirs()}
            if allowed:
                data["permissions"]["additionalDirectories"] = [d for d in allowed if d not in ours]
            for key in ("attribution", "includeCoAuthoredBy"):  # put back what you had, unless you changed it since
                rec = claude.get(key)
                if not rec or rec["prior"] == UNKNOWN or data.get(key, ABSENT) != rec["wrote"]:
                    if key in data and key not in kept:
                        kept.append(key)
                    continue
                if rec["prior"] == ABSENT:
                    data.pop(key, None)
                else:
                    data[key] = rec["prior"]
            if data.get("statusLine") == STATUSLINE:
                del data["statusLine"]
                saved = settings.load().get("your_statusline")
                if saved:
                    data["statusLine"] = saved
            return json.dumps(data, indent=2) + "\n"

        if undo_claude(read(P.claude_settings)) != read(P.claude_settings):
            out.append(
                Change(
                    P.claude_settings,
                    "take out LETS's folders and status line, and put back your attribution settings"
                    + (
                        " (kept as they are, since LETS can't tell what you had or you changed them: %s)"
                        % ", ".join(kept)
                        if kept
                        else ""
                    ),
                    edit=undo_claude,
                )
            )
    if P.codex_hooks.exists() and hooks_text(read(P.codex_hooks), add=False) != read(P.codex_hooks):
        out.append(Change(P.codex_hooks, "take out LETS's hooks", edit=lambda t: hooks_text(t, add=False)))
    if CODEX_ROOTS_TAG in read(P.codex_config) or CODEX_FALLBACK_TAG in read(P.codex_config):
        out.append(
            Change(
                P.codex_config,
                "take out LETS's folders and its CLAUDE.md fallback",
                edit=lambda t: "".join(
                    line
                    for line in t.splitlines(True)
                    if CODEX_ROOTS_TAG not in line and CODEX_FALLBACK_TAG not in line
                ),
            )
        )
    if is_ours(P.link) or (P.link.is_symlink() and os.path.realpath(str(P.link)) == str(ROOT.resolve())):
        out.append(Change(P.link, "remove the ~/lets link", apply=P.link.unlink))
    return out


def cmd_uninstall(a) -> None:
    agree(uninstall_changes(), "uninstall", a.yes, a.dry_run, one_by_one=False)
    if a.dry_run:
        return
    (P.state / LEDGER).unlink(missing_ok=True)  # done: a second uninstall changes nothing
    if codex_cli():
        run([codex_cli(), "plugin", "remove", "lets@%s" % MARKETPLACE], check=False)
        run([codex_cli(), "plugin", "marketplace", "remove", MARKETPLACE], check=False)
    ui.ok("Removed LETS's commands, its map, its guard and its links.")
    ui.note(
        "Kept: your profile and settings (%s), your planning repos, each repo's settings (`lets setup --remove` in "
        "a repo clears them), and backups of your files from before LETS (%s)."
        % (short_path(P.config), short_path(P.backups))
    )
    ui.step("remove the package itself: npm uninstall -g %s" % PACKAGE)


# ---------- update ----------


def latest_version(timeout: float = 20) -> str | None:
    """The newest LETS on the npm registry (only its version number is fetched)."""
    if not shutil.which("npm"):
        return None
    try:
        r = subprocess.run(
            ["npm", "view", PACKAGE, "version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    v = r.stdout.strip()
    return v if r.returncode == 0 and re.match(r"^\d+\.\d+\.\d+", v) else None


def newer(a: str, b: str) -> bool:
    """Is version a newer than version b?"""

    def key(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in re.findall(r"\d+", v.split("-")[0])[:3])

    return key(a) > key(b)


BEHAVIOUR = re.compile(
    r"^(plugin/skills/|plugin/refs/|plugin/hooks/|agent-hooks/|lib/lets/guard\.py|lib/lets/floor\.py|"
    r"AGENTS\.md|guides/)"
)


def release_diff(new_root: pathlib.Path) -> tuple[list[str], list[str]]:
    """(files that change how agents behave, all changed files) between this LETS and an unpacked newer one."""
    changed = []
    for base in (ROOT, new_root):
        for dp, dn, fns in os.walk(str(base)):
            dn[:] = [d for d in dn if d not in ("node_modules", "__pycache__", ".git")]
            for fn in fns:
                rel = os.path.relpath(os.path.join(dp, fn), str(base))
                a, b = ROOT / rel, new_root / rel
                if rel not in changed and (not a.exists() or not b.exists() or a.read_bytes() != b.read_bytes()):
                    changed.append(rel)
    changed.sort()
    return [c for c in changed if BEHAVIOUR.match(c)], changed


def changelog_since(new_root: pathlib.Path, old: str) -> str:
    text = read(new_root / "CHANGELOG.md")
    m = re.search(r"^## \[?%s\b" % re.escape(old), text, re.M)
    start = re.search(r"^## ", text, re.M)
    return text[start.start() if start else 0 : m.start() if m else 4000].strip()


def cmd_update(a) -> None:
    """Show what a newer LETS changes (its changelog, and which files change how agents behave), then install it."""
    have = version()
    ui.title("LETS update", "you have %s" % have)
    installed = settings.load().get("installed")
    if installed and installed != have:  # updated through npm directly: finish the job first
        ui.ok("LETS %s is installed, but its setup on this computer wasn't finished. Finishing it:" % have)
        sys.stdout.flush()
        os.execvp(str(ROOT / "bin" / "lets"), ["lets", "install"] + (["--yes"] if a.yes else []))
    new = latest_version()
    if new is None:
        raise LetsError("Couldn't reach the npm registry to look for a newer LETS. Check your connection, then re-run.")
    if not newer(new, have):
        ui.ok("You have the latest LETS (%s)." % have)
        return
    with tempfile.TemporaryDirectory(prefix="lets-update-") as tmp:
        r = run(["npm", "pack", "%s@%s" % (PACKAGE, new), "--silent"], cwd=tmp, check=False)
        tarball = (
            pathlib.Path(tmp) / r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else None
        )
        if tarball is None or not tarball.exists():
            raise LetsError("Couldn't download LETS %s: %s" % (new, (r.stderr or r.stdout).strip()[-300:]))
        run(["tar", "-xzf", str(tarball), "-C", tmp])
        new_root = pathlib.Path(tmp) / "package"
        behaviour, changed = release_diff(new_root)
        ui.out("LETS %s is out (you have %s)." % (new, have))
        ui.out()
        log = changelog_since(new_root, have)
        if log:
            ui.out(log)
            ui.out()
        if behaviour:
            ui.out(ui.paint("Changes how agents behave:", "bold"))
            for f in behaviour:
                ui.out("  " + f)
            ui.out()
        if any(f.startswith(("agent-hooks/", "plugin/hooks/")) for f in behaviour) and uses_codex():
            ui.note("Afterwards: Codex asks you to trust the changed hooks again (/hooks in Codex).")
        while True:
            pick = (
                "update"
                if a.yes
                else ui.select(
                    "Update to %s?" % new,
                    [
                        ("update", "Update", "install it and finish setting it up"),
                        ("show", "Show the exact changes", ""),
                        ("no", "Not now", ""),
                    ],
                    "update",
                )
            )
            if pick == "show":
                for f in behaviour or changed:
                    r = run(["diff", "-u", str(ROOT / f), str(new_root / f)], check=False)
                    ui.out(r.stdout or "(new or removed) %s" % f)
                continue
            if pick == "no":
                ui.ok("Nothing was changed.")
                return
            break
    r = run(["npm", "install", "-g", "%s@%s" % (PACKAGE, new)], check=False)
    if r.returncode != 0:
        raise LetsError("npm couldn't install LETS %s:\n%s" % (new, (r.stderr or r.stdout).strip()[-600:]))
    ui.ok("Installed LETS %s. Re-wiring it:" % new)
    os.execvp(str(P.link / "bin" / "lets"), ["lets", "install", "--yes"])
