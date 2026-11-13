"""Changes to files outside LETS: shown, agreed, backed up, then made.

Every file LETS edits outside its own package goes through here, so install, setup and doctor all preview the same
way, back up the same way, and can say exactly what was changed if they're interrupted.
"""

from __future__ import annotations

import difflib
import json
import os
import pathlib
import re
import shutil
from collections.abc import Callable

from . import ui
from .core import LetsError
from .paths import BEGIN, END, ROOT, P, short_path

Edit = Callable[[str], str]

# What the current command has changed so far: printed if it's cancelled or crashes part-way.
MADE: list[str] = []


class Change:
    """One change to one file. `edit` turns the file's old text into its new text, so several edits to one file can be
    combined into one change; `apply` is for changes that aren't text (links, clones, git config)."""

    def __init__(
        self,
        path: os.PathLike | str,
        summary: str,
        new: str | None = None,
        apply: Callable[[], None] | None = None,
        details: str | None = None,
        edit: Edit | None = None,
    ):
        self.path, self.summary, self._apply, self._details = pathlib.Path(path), summary, apply, details
        self.edit = edit if new is None else (lambda _old, new=new: new)

    @property
    def new(self) -> str | None:
        return self.edit(read(self.path)) if self.edit else None

    def details(self) -> str:
        if self._details:
            return self._details
        if self.edit is None:
            return self.summary
        diff = difflib.unified_diff(
            read(self.path).splitlines(), (self.new or "").splitlines(), "before", "after", lineterm="", n=1
        )
        return "\n".join(list(diff)[2:]) or "(no change)"

    def apply(self) -> None:
        if self.edit is not None:
            new = self.new or ""
            backup(self.path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(new)
        if self._apply:
            self._apply()
        MADE.append("%s: %s" % (short_path(self.path), self.summary))


def read(path: pathlib.Path) -> str:
    return path.read_text() if path.exists() else ""


def combined(changes: list[Change]) -> list[Change]:
    """One Change per file: text edits to the same file are chained, in order."""
    out: list[Change] = []
    by_path: dict[pathlib.Path, Change] = {}
    for c in changes:
        first = by_path.get(c.path)
        if first is not None and first.edit and c.edit and not first._apply and not c._apply:
            f, g = first.edit, c.edit
            first.edit = lambda old, f=f, g=g: g(f(old))
            first.summary += "; " + c.summary
            continue
        by_path.setdefault(c.path, c)
        out.append(c)
    return out


# ---------- backups ----------


def _backup_index() -> dict:
    f = P.backups / "index.json"
    return json.loads(f.read_text()) if f.exists() else {}


def backup(path: pathlib.Path) -> None:
    """Keep the first copy of any file LETS edits, as it was before LETS touched it."""
    index = _backup_index()
    key = str(path)
    if key in index:
        return
    if path.exists() and not path.is_symlink():
        dest = P.backups / key.strip("/").replace("/", "__")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(path), str(dest))
        index[key] = str(dest)
    else:
        index[key] = None  # LETS created it
    P.backups.mkdir(parents=True, exist_ok=True)
    (P.backups / "index.json").write_text(json.dumps(index, indent=2) + "\n")


# ---------- text helpers for the files LETS shares with you ----------


def block_text(path: pathlib.Path, body: str, text: str | None = None) -> str:
    """The file with LETS's marked block added or refreshed; everything else stays as it was."""
    text = read(path) if text is None else text
    block = "%s\n%s\n%s" % (BEGIN, body.rstrip(), END)
    if BEGIN in text and END in text:
        return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _m: block, text, flags=re.S)
    return (text.rstrip() + "\n\n" if text.strip() else "") + block + "\n"


def without_block(text: str) -> str:
    new = re.sub(r"\n*" + re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", "\n", text, flags=re.S)
    return new.strip() + ("\n" if new.strip() else "")


def json_of(path: pathlib.Path) -> dict:
    text = read(path)
    return json.loads(text) if text.strip() else {}


def is_ours(dst: pathlib.Path) -> bool:
    """A link LETS made (it points into ~/lets or the installed package)."""
    if not dst.is_symlink():
        return False
    target = os.path.expanduser(os.readlink(str(dst)))
    real, root, link = os.path.realpath(str(dst)), str(ROOT.resolve()), str(P.link)
    return target == link or target.startswith(link + os.sep) or real == root or real.startswith(root + os.sep)


def link_change(dst: pathlib.Path, src: pathlib.Path, summary: str) -> Change | None:
    """A Change that points dst at src, or None when it already does. Never replaces something LETS didn't make."""
    if dst.is_symlink() and os.path.realpath(str(dst)) == os.path.realpath(str(src)):
        return None
    if (dst.exists() or dst.is_symlink()) and not is_ours(dst):
        return None

    def make() -> None:
        if dst.is_symlink():
            dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(src)

    return Change(dst, summary, apply=make, details="a link to %s" % short_path(src))


# ---------- show, ask, make ----------


def agree(
    changes: list[Change], command: str, yes: bool = False, dry: bool = False, one_by_one: bool = True
) -> list[Change]:
    """Show the changes, ask, and make the agreed ones (safest first is the caller's order). Returns those made."""
    changes = combined(changes)
    if not changes:
        return []
    ui.title("LETS %s" % command, "changes · %d" % len(changes))
    width = max(len(short_path(c.path)) for c in changes) + 2
    for c in changes:
        ui.out("  " + short_path(c.path).ljust(width) + ui.paint(c.summary, "dim"))
    ui.out()
    if any(c.edit is not None for c in changes):
        ui.note(
            "Anything LETS edits is backed up first to %s; `lets uninstall` takes LETS's changes out."
            % short_path(P.backups)
        )
        ui.out()
    if dry:
        for c in changes:
            ui.out(ui.paint(short_path(c.path), "bold"))
            ui.out("\n".join("    " + line for line in c.details().splitlines()))
        ui.note("Dry run: nothing was changed.")
        return []
    if not ui.interactive() and not yes:
        raise LetsError(
            "Nothing was changed. Run `lets %s` in a terminal to review these, or add --yes to make them." % command
        )
    chosen = list(changes)
    while not yes:
        pick = ui.select(
            "Make these changes?",
            [("all", "Apply all", "")]
            + ([("one", "One by one", "choose for each file")] if one_by_one else [])
            + [("show", "Show the exact changes", ""), ("cancel", "Cancel", "change nothing")],
            "all",
        )
        if pick == "show":
            for c in changes:
                ui.out(ui.paint(short_path(c.path), "bold"))
                ui.out("\n".join("    " + line for line in c.details().splitlines()))
                ui.out()
            continue
        if pick == "cancel":
            raise LetsError("Nothing was changed.")
        if pick == "one":
            chosen = [
                c for c in changes if ui.confirm("%s: %s?" % (short_path(c.path), c.summary), True, "Yes", "Skip")
            ]
        break
    for c in chosen:
        c.apply()
    return chosen
