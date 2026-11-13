"""Run the floor guard over tests/floor_cases.json. Each case is [label, path, before, after, flagged?] for one file,
or [label, [[path, before, after], ...], flagged?] for several (before/after may be null: absent).
Usage: python3 tests/floor_cases.py   (prints one line per case; exit 1 if any case disagrees)"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
from lets import floor as floor_guard  # noqa: E402

cases = json.load(open(os.path.join(HERE, "floor_cases.json")))
work = tempfile.mkdtemp()
sh = lambda *a: subprocess.run(list(a), cwd=work, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
sh("git", "init", "-q")
sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
bad = 0
for case in cases:
    if len(case) == 3:
        label, changes, expect = case
    else:
        label, path, before, after, expect = case
        changes = [[path, before, after]]
    sh("git", "reset", "-q", "--hard")
    sh("git", "clean", "-qfdx")
    for path, before, _after in changes:
        if before is not None:
            full = os.path.join(work, path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            open(full, "w").write(before)
    sh("git", "add", "-A")
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "before")
    for path, _before, after in changes:
        full = os.path.join(work, path)
        if after is None:
            if os.path.exists(full):
                os.remove(full)
        else:
            os.makedirs(os.path.dirname(full), exist_ok=True)
            open(full, "w").write(after)
    sh("git", "add", "-A")
    got = bool(floor_guard.check(["--cached"], work))
    ok = got == expect
    bad += not ok
    print("  %s %s (flagged=%s)" % ("ok  " if ok else "FAIL", label, got))
sys.exit(1 if bad else 0)
