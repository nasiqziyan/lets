"""Entry point for the LETS guard (lib/lets/guard.py). Kept to old syntax so any python3 can run it and say why it
can't go on: when the guard can't run, git, gh and glab commands are blocked and everything else passes."""
import os
import sys

LIB = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib")
SHIPS = ("git", "gh", "glab")


def fail_closed(why):
    raw = sys.stdin.read()
    words = raw.replace('"', " ").replace("'", " ").replace(";", " ").replace("&", " ").replace("|", " ").split()
    if any(w in SHIPS or w.endswith(tuple("/" + s for s in SHIPS)) for w in words):
        sys.stderr.write("Blocked: the LETS guard can't run (%s), so git, gh and glab commands are blocked until it "
                         "can. Run `lets doctor`.\n" % why)
        sys.exit(2)
    sys.exit(0)


if sys.version_info < (3, 11):  # noqa: UP036  (this check is for older Pythons)
    fail_closed("Python %d.%d; LETS needs 3.11 or newer" % sys.version_info[:2])
sys.path.insert(0, LIB)
try:
    from lets.guard import entry
except Exception as e:  # noqa: BLE001
    fail_closed("%s: %s" % (type(e).__name__, e))
entry()
