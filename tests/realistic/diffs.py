"""Replay recorded diffs on the realistic repo and check what the floor guard does with each: "block" (an agent's
commit is blocked), "ask" (the walkthrough asks about it) or "none". The cases are the sixth, seventh and eighth
independent testers' ordinary, weakening and targeted changes, the eighth on a legacy codebase; the weakening ones it misses are in tests/floor_known_gaps.json.
Usage: python3 diffs.py <lib> <origin.git made by mkrepo.sh> <work dir>   (exit 1 if any case disagrees)"""
import json
import os
import shutil
import subprocess
import sys

lib, origin, work = sys.argv[1:4]
sys.path.insert(0, lib)
from lets import floor as floor_guard  # noqa: E402

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@example.com")


def sh(*a, cwd=None):
    subprocess.run(list(a), cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=ENV)


def put(root, path, text):
    full = os.path.join(root, path)
    if text is None:
        if os.path.exists(full):
            os.remove(full)
        return
    os.makedirs(os.path.dirname(full) or root, exist_ok=True)
    with open(full, "w") as f:
        f.write(text)


shutil.rmtree(work, ignore_errors=True)
base = os.path.join(work, "base")
sh("git", "clone", "-q", "-b", "feat/order-overlay", origin, base)
bad, tally = 0, {}
for n, (label, files, expect) in enumerate(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "diffs.json"))), 1):
    d = os.path.join(work, "c%03d" % n)
    shutil.copytree(base, d, symlinks=True)
    for path, before, _after in files:
        put(d, path, before)
    sh("git", "add", "-A", cwd=d)
    sh("git", "commit", "-qm", "before", "--allow-empty", cwd=d)
    for path, _before, after in files:
        put(d, path, after)
    sh("git", "add", "-A", cwd=d)
    found = floor_guard.check(["--cached"], d)
    got = "block" if any(floor_guard.blocking(f) for f in found) else "ask" if found else "none"
    tally[got] = tally.get(got, 0) + 1
    if got != expect:
        bad += 1
        print("  %s: expected %s, got %s %s" % (label, expect, got, found[:3]))
    shutil.rmtree(d)
print("  %d diffs: %s" % (sum(tally.values()), ", ".join("%d %s" % (v, k) for k, v in sorted(tally.items()))))
sys.exit(1 if bad else 0)
