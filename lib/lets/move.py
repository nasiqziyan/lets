"""Moving plans to another home, when `lets setup` is re-run with a different answer to "Where should the plans live?".

Plans are copied (not their history): into the repo's plans/ on a branch `lets-plans`, uncommitted, for you to review
and open a pull request; or from plans/ into a planning repo, committed there locally. The old home is left untouched.
When the new home already has plans (a teammate already uses LETS there), every clash is asked about, with the
difference shown and a default that loses nothing. Not offered for a group's planning repo: it serves several repos.
"""

from __future__ import annotations

import pathlib
import re
import shutil
from dataclasses import dataclass, field

from . import ui
from .changes import Change
from .core import LetsError, git, git_config, run
from .paths import short_path

WORDS_FILES = ("CODING_STANDARDS.md", "CONSTRAINTS.md")


@dataclass
class Move:
    repo: pathlib.Path
    src: pathlib.Path
    dest: pathlib.Path
    into_repo: bool
    who: str
    copies: list[tuple[pathlib.Path, pathlib.Path]] = field(default_factory=list)  # (from, to) files
    edits: list[tuple[pathlib.Path, str]] = field(default_factory=list)  # (to, new text) merged files
    renames: dict[str, str] = field(default_factory=dict)  # old link text -> new, applied to copied Markdown
    on_branches: dict[str, list[tuple[pathlib.Path, str]]] = field(default_factory=dict)  # branch -> (from, rel)
    left: list[str] = field(default_factory=list)  # open changes left in the old home
    worktrees: list[str] = field(default_factory=list)

    def change(self) -> Change:
        what = "copy the plans from %s%s" % (
            short_path(self.src),
            " onto a new branch lets-plans (uncommitted)"
            if self.into_repo
            else " into this planning repo (committed locally)",
        )
        lines = ["%s -> %s" % (rel(a, self.src), rel(b, self.dest)) for a, b in self.copies]
        lines += ["%s: merged" % rel(p, self.dest) for p, _t in self.edits]
        lines += ["%s: onto branch %s" % (r, b) for b, items in self.on_branches.items() for _s, r in items]
        lines += ["%s: left in %s" % (c, short_path(self.src)) for c in self.left]
        return Change(self.dest, what, apply=self.apply, details="\n".join(lines) or "nothing to copy")

    def apply(self) -> None:
        if self.into_repo:
            if git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.repo, check=False) != "lets-plans":
                git("switch", "-c", "lets-plans", cwd=self.repo) if not branch_exists(self.repo, "lets-plans") else git(
                    "switch", "lets-plans", cwd=self.repo
                )
        for a, b in self.copies:
            write_copy(a, b, self.renames)
        for p, text in self.edits:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        for branch, items in self.on_branches.items():
            wt = self.repo.parent / ("%s-%s" % (self.repo.name, re.sub(r"[^\w.-]", "-", branch)))
            run(["git", "worktree", "add", "--quiet", str(wt), branch], cwd=self.repo)
            for s, r in items:
                write_copy(s, wt / "plans" / r, self.renames)
            self.worktrees.append(str(wt))
        if not self.into_repo:
            git("add", "-A", cwd=self.dest)
            if git("status", "--porcelain", cwd=self.dest):
                run(
                    ["git", "commit", "-q", "--no-verify", "-m", "lets setup: plans moved from %s" % self.repo.name],
                    cwd=self.dest,
                )

    def finish(self) -> None:
        if self.into_repo:
            ui.ok(
                "Plans copied into %s on the branch lets-plans, uncommitted. Review them, commit, and open a pull "
                "request." % short_path(self.dest)
            )
        else:
            ui.ok(
                "Plans copied into %s and committed there. The repo's plans/ folder is left for you to remove in a "
                "pull request." % short_path(self.dest)
            )
        for wt in self.worktrees:
            ui.note(
                "A change's plan went onto its own branch in %s (uncommitted): commit it there, then "
                "`git worktree remove %s`." % (short_path(wt), short_path(wt))
            )
        ui.note("The old home (%s) is untouched." % short_path(self.src))


def rel(p: pathlib.Path, base: pathlib.Path) -> str:
    try:
        return str(p.relative_to(base))
    except ValueError:
        return str(p)


def branch_exists(repo: pathlib.Path, name: str) -> bool:
    return bool(git("rev-parse", "--verify", "--quiet", "refs/heads/" + name, cwd=repo, check=False))


def write_copy(a: pathlib.Path, b: pathlib.Path, renames: dict[str, str]) -> None:
    b.parent.mkdir(parents=True, exist_ok=True)
    if a.suffix == ".md" and renames:
        text = a.read_text()
        for old, new in renames.items():
            text = text.replace(old, new)
        b.write_text(text)
    else:
        shutil.copy2(str(a), str(b))


def files(root: pathlib.Path) -> list[pathlib.Path]:
    """The plan files under a folder, without git's files, the planning repo's own README and repo list, and
    OpenSpec's config (setup writes the current one)."""
    out = []
    for p in sorted(root.rglob("*")):
        parts = p.relative_to(root).parts
        if (
            p.is_file()
            and not ({".git", ".lets"} & set(parts))
            and "/".join(parts) not in ("README.md", "repos.json", "openspec/config.yaml")
        ):
            out.append(p)
    return out


def plan_for(
    repo: pathlib.Path, was: tuple[pathlib.Path | None, str | None], planning: str, dest: pathlib.Path | None
) -> Move | None:
    """The move a home change needs (asking about each clash now), or None when there's nothing to move."""
    src, home = was
    if src is None or dest is None or not src.exists() or src.resolve() == dest.resolve() or home == planning:
        return None
    if home in ("team", "private"):
        group = (src / "repos.json").exists() and len(
            __import__("json").loads((src / "repos.json").read_text()).get("repos", {})
        ) > 1
        if group:
            ui.note(
                "%s's plans stay in %s: it's a group's planning repo, serving several repos." % (repo.name, src.name)
            )
            return None
    into_repo = planning == "in-repo"
    if not ui.confirm(
        "Bring the plans in from %s?" % short_path(src),
        True,
        "Yes, copy them",
        "No, start empty",
        "They're copied, not moved: %s stays as it is." % short_path(src),
    ):
        return None
    who = (git_config("user.name", repo).split() or [src.name])[0].lower()
    m = Move(repo, src, dest, into_repo, who)
    open_changes = (
        sorted(p.name for p in (src / "openspec" / "changes").iterdir() if p.is_dir() and p.name != "archive")
        if (src / "openspec" / "changes").exists()
        else []
    )
    skip_paths: set[pathlib.Path] = set()
    for name in open_changes:
        where = ask_open_change(repo, name, into_repo)
        folder = src / "openspec" / "changes" / name
        if where == "leave":
            m.left.append(name)
            skip_paths |= set(files(folder))
        elif where.startswith("branch:"):
            m.on_branches.setdefault(where[7:], []).extend((f, str(f.relative_to(src))) for f in files(folder))
            skip_paths |= set(files(folder))
    plan_folders(m, src, dest, skip_paths)
    return m


def ask_open_change(repo: pathlib.Path, name: str, into_repo: bool) -> str:
    branch = next(
        (
            b
            for b in git("for-each-ref", "--format=%(refname:short)", "refs/heads", cwd=repo, check=False).splitlines()
            if name in b
        ),
        None,
    )
    opts = (
        [("branch:" + branch, "Onto its branch, %s" % branch, "uncommitted, in a worktree of its own")]
        if into_repo and branch
        else []
    ) + [
        ("rest", "With the rest", "on lets-plans" if into_repo else "with the other plans"),
        ("leave", "Leave it where it is", "bring it in later"),
    ]
    return ui.select("The change %s is still open. Where should it go?" % name, opts, opts[0][0])


def plan_folders(m: Move, src: pathlib.Path, dest: pathlib.Path, skip: set[pathlib.Path]) -> None:
    """Fill in the move: plain copies, and a question for each clash."""
    renamed_dirs: dict[pathlib.Path, pathlib.Path] = {}
    for kind in ("epics", "openspec/changes", "openspec/changes/archive", "research"):
        for d in sorted((src / kind).iterdir()) if (src / kind).exists() else []:
            target = dest / kind / d.name
            if d.is_dir() and d.name != "archive" and target.exists() and set(files(d)) - skip:
                new = ask_name_clash(kind, d.name, dest / kind)
                if new is None:
                    skip |= set(files(d))
                else:
                    renamed_dirs[d] = dest / kind / new
                    m.renames["%s/%s" % (kind, d.name)] = "%s/%s" % (kind, new)
    adrs = adr_renumbering(src, dest)
    for a, b in adrs.items():
        m.renames[a.name] = b.name
    for f in files(src):
        if f in skip:
            continue
        r = f.relative_to(src)
        target = next((nd / f.relative_to(od) for od, nd in renamed_dirs.items() if od in f.parents), dest / r)
        if f in adrs:
            target = adrs[f]
        if not target.exists() or target.read_bytes() == f.read_bytes():
            if not target.exists():
                m.copies.append((f, target))
            continue
        merge_clash(m, f, target)


def ask_name_clash(kind: str, name: str, parent: pathlib.Path) -> str | None:
    n = 2
    while (parent / ("%s-%d" % (name, n))).exists():
        n += 1
    suggested = "%s-%d" % (name, n)
    what = {"epics": "an epic", "research": "research"}.get(kind, "a change")
    pick = ui.select(
        "The new home already has %s called %s. What should yours be?" % (what, name),
        [
            ("two", "Bring it in as %s" % suggested, "links to it are updated"),
            ("name", "Rename it", "type a name"),
            ("skip", "Skip it", "it stays only in the old home"),
        ],
        "two",
    )
    if pick == "skip":
        return None
    if pick == "name":
        while True:
            typed = ui.text("New name for %s?" % name, suggested) or suggested
            if not (parent / typed).exists():
                return typed
            ui.warn("%s exists there too." % typed)
    return suggested


def adr_renumbering(src: pathlib.Path, dest: pathlib.Path) -> dict[pathlib.Path, pathlib.Path]:
    """Incoming ADRs numbered after the new home's highest, so numbers never clash."""
    theirs = sorted((src / "docs" / "adr").glob("[0-9]*.md")) if (src / "docs" / "adr").exists() else []
    ours = sorted((dest / "docs" / "adr").glob("[0-9]*.md")) if (dest / "docs" / "adr").exists() else []
    if not theirs or not ours:
        return {}
    top = max(int(re.sub(r"\D.*", "", p.name)) for p in ours)
    width = len(re.sub(r"\D.*", "", ours[0].name))
    out = {}
    for i, p in enumerate(theirs, 1):
        rest = re.sub(r"^\d+", "", p.name)
        out[p] = dest / "docs" / "adr" / ("%0*d%s" % (width, top + i, rest))
    if out:
        ui.note("ADRs renumbered after %s's highest (%d):" % (short_path(dest), top))
        for a, b in out.items():
            ui.out("    %s  ->  %s" % (a.name, b.name))
    return out


def diff_text(a: pathlib.Path, b: pathlib.Path) -> str:
    return run(["diff", "-u", str(b), str(a)], check=False).stdout or "(the same)"


def merge_clash(m: Move, mine: pathlib.Path, theirs: pathlib.Path) -> None:
    """Both homes have this file with different text: ask, with a default that loses nothing."""
    r = rel(theirs, m.dest)
    if theirs.name == "GLOSSARY.md":
        m.edits.append((theirs, merge_glossary(theirs.read_text(), mine.read_text(), m.who)))
        return
    if theirs.name in WORDS_FILES:
        opts = [
            ("below", "Add yours below theirs", "under '## From %s's plans'" % m.who),
            ("keep", "Keep the repo's", ""),
            ("mine", "Use yours", ""),
            ("diff", "Show the difference", ""),
        ]
        new = {
            "below": lambda: theirs.read_text().rstrip() + "\n\n## From %s's plans\n\n%s" % (m.who, mine.read_text()),
            "mine": mine.read_text,
        }
    elif "specs" in theirs.parts:
        opts = [
            ("beside", "Keep theirs, and put yours beside it", "as from-%s.md" % m.who),
            ("keep", "Keep theirs", ""),
            ("mine", "Use yours", ""),
            ("diff", "Show the difference", ""),
        ]
        new = {"mine": mine.read_text}
    else:
        opts = [
            (
                "beside",
                "Keep both",
                "yours as %s" % theirs.with_name(theirs.stem + "-from-" + m.who + theirs.suffix).name,
            ),
            ("keep", "Keep theirs", ""),
            ("mine", "Use yours", ""),
            ("diff", "Show the difference", ""),
        ]
        new = {"mine": mine.read_text}
    while True:
        pick = ui.select("%s differs between the two homes. What should it hold?" % r, opts, opts[0][0])
        if pick != "diff":
            break
        ui.out(diff_text(mine, theirs))
    if pick == "keep":
        return
    if pick == "beside":
        name = ("from-%s.md" % m.who) if "specs" in theirs.parts else theirs.stem + "-from-" + m.who + theirs.suffix
        m.copies.append((mine, theirs.with_name(name)))
        return
    m.edits.append((theirs, new[pick]()))


def glossary_terms(text: str) -> dict[str, str]:
    """{term: definition} from a glossary of '**Term**: definition' lines or '## Term' sections."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        hit = re.match(r"^\s*[-*]?\s*\*\*(.+?)\*\*\s*[:—-]\s*(.+)$", line)
        if hit:
            out[hit.group(1).strip()] = hit.group(2).strip()
    for hit in re.finditer(r"^##+\s+(.+?)\n(.*?)(?=^##|\Z)", text, re.M | re.S):
        out.setdefault(hit.group(1).strip(), hit.group(2).strip())
    return out


def merge_glossary(theirs: str, mine: str, who: str) -> str:
    """New terms are added; the same term with the same definition is skipped; a different definition is asked."""
    have, incoming = glossary_terms(theirs), glossary_terms(mine)
    added = []
    for term, definition in incoming.items():
        if term not in have:
            added.append("- **%s**: %s" % (term, definition))
        elif have[term].strip() != definition.strip():
            pick = ui.select(
                "The glossary defines '%s' differently. Which should it keep?" % term,
                [
                    ("theirs", "Keep the repo's", have[term][:90]),
                    ("mine", "Use yours", definition[:90]),
                    ("both", "Keep both", "yours as '%s (%s)'" % (term, who)),
                ],
                "theirs",
            )
            if pick == "mine":
                theirs = theirs.replace(have[term], definition, 1)
            elif pick == "both":
                added.append("- **%s (%s)**: %s" % (term, who, definition))
    if added:
        theirs = theirs.rstrip() + "\n\n" + "\n".join(added) + "\n"
    return theirs


def check_target(dest: pathlib.Path) -> None:
    if dest.exists() and not dest.is_dir():
        raise LetsError("%s isn't a folder." % short_path(dest))
