"""`lets check` (weakened gates in this branch's changes) and `lets walkthrough` (what still needs walking through)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

from . import floor, walkthrough
from .core import LetsError, git, git_config, say
from .planning import repo_root


def cmd_check(a) -> None:
    """The floor check on everything this branch changes, committed or not."""
    root = str(repo_root())
    if not git("rev-parse", "--verify", "--quiet", "HEAD", cwd=root, check=False):
        say("This repo has no commits yet: nothing to check.")
        return
    base = walkthrough.default_base(root)
    index = git("rev-parse", "--git-path", "index", cwd=root)
    fd, tmp = tempfile.mkstemp(prefix="lets-check-")
    os.close(fd)
    try:
        shutil.copyfile(index if os.path.isabs(index) else os.path.join(root, index), tmp)
        env = dict(os.environ, GIT_INDEX_FILE=tmp)
        subprocess.run(["git", "add", "-A"], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        found = floor.check(["--cached", base], root, env)
    finally:
        os.remove(tmp)
    block = [f for f in found if floor.blocking(f)]
    asks = [f for f in found if not floor.blocking(f)]
    if block:
        say("Switches a check off (an agent would be blocked; approve with git config --add branch.<name>.letsAllow):")
        for f in block:
            say("  %s: %s" % f)
    if asks:
        say("Loosens a check (the walkthrough asks about these):")
        for f in asks:
            say("  %s: %s" % f)
    if not found:
        say("No weakened gates in this branch's changes (against %s)." % base[:12])
    chk = git_config("lets.check", root)
    if a.run:
        if not chk:
            say("No quick check is set for this repo (`lets setup` asks for one).")
            return
        say("Running %s" % chk)
        raise SystemExit(subprocess.run(["sh", "-c", chk], cwd=root).returncode)


def cmd_walkthrough(a) -> None:
    root = str(repo_root())
    if not git("rev-parse", "--verify", "--quiet", "HEAD", cwd=root, check=False):
        raise LetsError("This repo has no commits yet, so there's nothing to walk through.")
    if a.action == "complete":
        try:
            asks = walkthrough.questions(root)
            files = walkthrough.record_pass(root)
        except RuntimeError as e:
            raise LetsError("Nothing recorded: %s" % e) from None
        branch = git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=root, check=False)
        if branch:
            git("config", "branch.%s.lets-walked" % branch, git("rev-parse", "HEAD", cwd=root), cwd=root)
        say("Walkthrough complete for %d changed file%s on this branch." % (len(files), "" if len(files) == 1 else "s"))
        if asks:
            say("It also accepts these changes, which loosen a check:")
            for f in asks:
                say("  %s: %s" % f)
    elif a.action == "scope":
        base, todo = walkthrough.scope(root)
        say("base %s" % base)
        for p in todo:
            say(p)
        for f in walkthrough.questions(root):
            say("ask: %s: %s" % f)
        pending = walkthrough.uncommitted(root)
        if pending:
            sys.stderr.write("uncommitted (commit before the walkthrough): %s\n" % ", ".join(pending))
    else:
        base, todo = walkthrough.scope(root)
        say("%d changed file(s) still need a walkthrough (base %s)" % (len(todo), base[:12]))
