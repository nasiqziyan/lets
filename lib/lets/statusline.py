"""`lets statusline`: Claude Code's status line. One line, from the branch you're on:

    shop-checkout ●◉○○ › take-card-payment ●●◉○ › Validate the card number   ✎ pair

The epic (its changes: done, this one, still to come), the change (its tasks), the task in hand, and the mode. A
finished change shows what's next instead of a task; a patch shows `patch › <name>`. Outside a LETS branch it prints
nothing. Claude Code passes a JSON description of the session on stdin; only its folder is used.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

DONE, NOW, TODO = "●", "◉", "○"
MODES = {"pair": "✎ pair", "agent": "⚙ agent"}
CODES = {"epic": "35", "change": "36", "task": "37", "dim": "2"}
TITLE_MAX = 32


def paint(text: str, style: str) -> str:
    if "NO_COLOR" in os.environ or not text:
        return text
    return "\033[%sm%s\033[0m" % (CODES[style], text)


def git(cwd: str, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return r.stdout.strip() if r.returncode == 0 else ""


def config(cwd: str) -> dict[str, str]:
    """This repo's lets.* settings and branch notes, read in one go."""
    out = {}
    raw = git(cwd, "config", "-z", "--get-regexp", r"^(lets\.|branch\..*\.lets-)")
    for entry in raw.split("\0"):
        key, _, value = entry.partition("\n")
        if key:
            out[key.lower()] = value
    return out


def tasks(tasks_md: pathlib.Path) -> list[tuple[str, bool]]:
    """[(title, done)] for each numbered group of a tasks.md."""
    out: list[list] = []
    for line in tasks_md.read_text().splitlines() if tasks_md.exists() else []:
        head = re.match(r"^##\s+\d+\.\s+(.+?)\s*$", line)
        if head:
            out.append([head.group(1), True, False])
        elif out and re.match(r"^\s*[-*]\s+\[[ xX]\]", line):
            out[-1][2] = True
            if re.match(r"^\s*[-*]\s+\[ \]", line):
                out[-1][1] = False
    return [(t, done and any_steps) for t, done, any_steps in out]


def label(path: pathlib.Path, key: str) -> str:
    f = path / ".openspec.yaml"
    hit = re.search(r"^%s:\s*(\S+)" % re.escape(key), f.read_text(), re.M) if f.exists() else None
    return hit.group(1).strip("'\"") if hit else ""


def epic_changes(proot: pathlib.Path, epic: str) -> list[str]:
    """The epic's changes in delivery order: the `## Changes` list in its map."""
    m = proot / "epics" / epic / "map.md"
    text = m.read_text() if m.exists() else ""
    section = re.search(r"^##\s+Changes\s*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    names = re.findall(r"^\s*(?:[-*]|\d+\.)\s+`?([a-z0-9][a-z0-9-]*)`?", section.group(1), re.M) if section else []
    return names


def archived(proot: pathlib.Path, name: str) -> bool:
    d = proot / "openspec" / "changes" / "archive"
    return d.exists() and any(re.match(r"^\d{4}-\d{2}-\d{2}-%s$" % re.escape(name), p.name) for p in d.iterdir())


def planning_root(top: str, cfg: dict[str, str]) -> pathlib.Path | None:
    if cfg.get("lets.plans"):
        return pathlib.Path(os.path.expanduser(cfg["lets.plans"]))
    p = pathlib.Path(top) / "plans"
    return p if (p / "openspec").exists() else None


def infer_change(proot: pathlib.Path, branch: str) -> str:
    d = proot / "openspec" / "changes"
    names = [p.name for p in d.iterdir() if p.is_dir() and p.name != "archive"] if d.exists() else []
    hits = [n for n in names if n in branch]
    return hits[0] if len(hits) == 1 else ""


def line(cwd: str, width: int = 120) -> str:
    top = git(cwd, "rev-parse", "--show-toplevel")
    if not top:
        return ""
    branch = git(top, "symbolic-ref", "--quiet", "--short", "HEAD")
    if not branch:
        return ""
    cfg = config(top)
    note = "branch.%s." % branch.lower()
    mode = MODES.get(cfg.get(note + "lets-mode") or cfg.get("lets.build", ""), "")
    patch = cfg.get(note + "lets-patch")
    if patch:
        return "%s › %s%s" % (paint("patch", "dim"), paint(patch, "change"), "   " + mode if mode else "")
    proot = planning_root(top, cfg)
    if proot is None:
        return ""
    change = cfg.get(note + "lets-change") or infer_change(proot, branch)
    folder = proot / "openspec" / "changes" / change
    if not change or not folder.exists():
        return ""
    groups = tasks(folder / "tasks.md")
    current = next((i for i, (_t, done) in enumerate(groups) if not done), None)
    task_dots = "".join(DONE if done else NOW if i == current else TODO for i, (_t, done) in enumerate(groups))
    if current is None:
        reviewed = cfg.get(note + "lets-reviewed")
        head = git(top, "rev-parse", "HEAD")
        walked = cfg.get(note + "lets-walked")
        tail = paint(
            "next: " + ("close" if walked and walked == head else "walkthrough" if reviewed == head else "review"),
            "dim",
        )
    else:
        title = groups[current][0]
        tail = paint(title if len(title) <= TITLE_MAX else title[: TITLE_MAX - 1] + "…", "task")
    epic = label(folder, "x-lets-epic")
    epic_part = ""
    if epic:
        order = epic_changes(proot, epic)
        dots = "".join(NOW if n == change else DONE if archived(proot, n) else TODO for n in order)
        epic_part = paint(epic, "epic") + (" " + dots if dots else "") + " › "
    parts = [
        epic_part,
        paint(change, "change"),
        " " + task_dots if task_dots else "",
        " › ",
        tail,
        "   " + mode if mode else "",
    ]
    text = "".join(parts)
    plain = re.sub(r"\033\[[0-9;]*m", "", text)
    if len(plain) > width:  # narrow: drop the task title, then the epic's dots
        parts[3:5] = ["", ""]
        text = "".join(parts)
        if len(re.sub(r"\033\[[0-9;]*m", "", text)) > width and epic:
            parts[0] = paint(epic, "epic") + " › "
            text = "".join(parts)
    return text


def cmd_statusline(a=None) -> None:
    if a is not None and getattr(a, "action", None):
        from .install import cmd_statusline_switch

        cmd_statusline_switch(a)
        return
    try:
        data = json.loads(sys.stdin.read() or "{}") if not sys.stdin.isatty() else {}
    except ValueError:
        data = {}
    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or os.getcwd()
    width = shutil.get_terminal_size((120, 20)).columns
    try:
        print(line(cwd, width))
    except Exception:  # noqa: BLE001  a status line never shows an error
        print("")
