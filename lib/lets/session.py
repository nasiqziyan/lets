"""What LETS says at the start of a session, and its once-a-day update check.

The session-start hook prints only when something needs saying (an agent reads it and tells you): the guard can't
run, LETS changed and needs `lets update` to finish, or a newer LETS is out. The update check asks the npm registry for the
latest version number, at most once a day, and only when your profile says to (LETS_NO_UPDATE_CHECK=1 turns it off).
"""

from __future__ import annotations

import json
import os
import pathlib
import time

from . import profile, settings
from .paths import P, version

DAY = 24 * 3600


def updates_on() -> bool:
    return not os.environ.get("LETS_NO_UPDATE_CHECK") and profile.answer("updates") == "on"


def newer_version(max_age: float = DAY) -> str | None:
    """A newer LETS's version, if there is one (asked at most once a day; the answer is cached)."""
    if not updates_on():
        return None
    f = P.cache / "update.json"
    try:
        cached = json.loads(f.read_text()) if f.exists() else {}
    except ValueError:
        cached = {}
    if time.time() - cached.get("checked", 0) > max_age:
        from .install import latest_version

        cached = {"checked": time.time(), "latest": latest_version(timeout=5)}
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(cached))
    latest = cached.get("latest")
    from .install import newer

    return latest if latest and newer(latest, version()) else None


def notice() -> str | None:
    """The one-line update notice for lets commands."""
    try:
        v = newer_version()
    except Exception:  # noqa: BLE001  never let a notice get in the way
        return None
    return "LETS %s is out (you have %s): run `lets update`." % (v, version()) if v else None


def cmd_session_start(a=None) -> None:
    lines = []
    from .doctor import problems

    try:
        broken = [p.text for p in problems() if "guard" in p.text or "python3" in p.text]
    except Exception as e:  # noqa: BLE001
        broken = ["LETS's checks couldn't run (%s)" % e]
    if broken:
        lines.append(
            "The LETS guard may not be protecting this session: %s. Tell me this before anything else, and "
            "ask me to run `lets doctor`." % "; ".join(broken)
        )
    installed = settings.load().get("installed")
    if installed and installed != version():
        lines.append(
            "LETS was updated to %s but its setup on this computer wasn't finished (it was %s). Tell me to run "
            "`lets update`: it finishes the job." % (version(), installed)
        )
    try:
        from .core import git
        from .upgrade import SETUP_VERSION, is_outdated, set_up_by

        top = git("rev-parse", "--show-toplevel", check=False)
        if top and is_outdated(pathlib.Path(top)):
            lines.append(
                "This repo was set up by %s. Tell me to run `lets setup` here: it asks only what's new in %s "
                "and keeps my other answers." % (set_up_by(pathlib.Path(top)), SETUP_VERSION)
            )
    except Exception:  # noqa: BLE001  never let a notice get in the way
        pass
    n = notice()
    if n:
        lines.append(n + " Mention it to me once, briefly.")
    if lines:
        print("LETS: " + "\nLETS: ".join(lines))
