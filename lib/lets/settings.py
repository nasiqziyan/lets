"""LETS's own settings file, ~/.config/lets/config.json. Paths are stored ~-relative so the file can be carried to
another computer (docs/how-to/settings-on-two-computers.md)."""

from __future__ import annotations

import json
import pathlib

from .paths import P, expand, tilde


def load() -> dict:
    f = P.settings
    return json.loads(f.read_text()) if f.exists() and f.read_text().strip() else {}


def save(data: dict) -> None:
    P.settings.parent.mkdir(parents=True, exist_ok=True)
    P.settings.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def plans_dirs() -> list[pathlib.Path]:
    """The folders planning repos are kept in on this computer (each chosen at setup)."""
    return [expand(d) for d in load().get("plans_dirs", []) if d]


def notes_dir() -> pathlib.Path | None:
    """Where /lets:learn saves notes: LETS's folder unless you chose your own, None if you chose no notes."""
    where = load().get("notes")
    if where == "off":
        return None
    return expand(where) if where else P.learning


def set_notes_dir(where: str | None) -> None:
    """None: LETS's folder; "off": no notes; else a folder, stored ~-relative."""
    data = load()
    if where is None:
        data.pop("notes", None)
    else:
        data["notes"] = where if where == "off" else tilde(expand(where))
    save(data)


def remember_plans_dir(d: pathlib.Path) -> None:
    data = load()
    dirs = data.setdefault("plans_dirs", [])
    if tilde(d) not in dirs:
        dirs.append(tilde(d))
    save(data)
