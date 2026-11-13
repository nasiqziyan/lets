"""Small helpers every command uses: running programs, git, and LETS's one error type."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence


class LetsError(Exception):
    """A problem the person can act on. The CLI prints the message (no traceback) and exits 1."""


def run(
    cmd: Sequence[object],
    cwd: os.PathLike | str | None = None,
    check: bool = True,
    env: dict | None = None,
    input: str | None = None,
) -> subprocess.CompletedProcess:
    r = subprocess.run(
        [str(c) for c in cmd],
        cwd=None if cwd is None else str(cwd),
        env=env,
        text=True,
        input=input,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and r.returncode != 0:
        raise LetsError("%s failed:\n%s" % (" ".join(map(str, cmd)), (r.stderr or r.stdout).strip()))
    return r


def git(*args: object, cwd: os.PathLike | str | None = None, check: bool = True) -> str:
    return run(["git", *args], cwd=cwd, check=check).stdout.strip()


def git_config(key: str, cwd: os.PathLike | str | None = None) -> str:
    """One git config value, or "" when it isn't set."""
    return git("config", "--get", key, cwd=cwd, check=False)


def say(msg: str = "") -> None:
    print(msg, flush=True)
