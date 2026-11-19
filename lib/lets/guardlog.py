"""`lets guard log`: what the guard blocked, asked about or crashed on lately, so a wrong block is easy to report."""

from __future__ import annotations

import json
import time

from .core import say
from .paths import ISSUES, P

LOG = P.cache / "guard.log"
WORDS = {"block": "blocked", "ask": "asked you", "crash": "crashed"}


def entries(days: float | None = None) -> list[dict]:
    try:
        lines = LOG.read_text().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if days is None or time.time() - e.get("time", 0) <= days * 86400:
            out.append(e)
    return out


def doctor_lines() -> list[str]:
    """What `lets doctor` says about the last week: a count, and a nudge to report crashes."""
    recent = entries(days=7)
    if not recent:
        return []
    counts = {k: sum(1 for e in recent if e.get("kind") == k) for k in WORDS}
    said = ", ".join("%s %d time%s" % (WORDS[k], n, "" if n == 1 else "s") for k, n in counts.items() if n)
    lines = ["  guard, last 7 days: %s. `lets guard log` shows them." % said]
    if counts["crash"]:
        lines.append(
            "  The guard crashed: that's a bug in LETS. Please report it at %s/new with the lines from "
            "`lets guard log`." % ISSUES
        )
    return lines


def cmd_guard_log(a) -> None:
    shown = entries()[-(a.last or 20) :]
    if not shown:
        say("The guard hasn't blocked anything, asked you anything or crashed lately.")
        return
    for e in shown:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(e.get("time", 0)))
        say("%s  %s: %s" % (when, WORDS.get(e.get("kind"), e.get("kind")), e.get("why", "").splitlines()[0]))
        if e.get("command"):
            say("      %s" % e["command"].replace("\n", "\n      "))
    say()
    say("If one of these was wrong, please report it: %s/new (paste the lines above; take out anything private)." % ISSUES)
