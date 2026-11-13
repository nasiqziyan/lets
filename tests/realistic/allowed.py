"""Feed every entry of a corpus to the guard and report any that it doesn't allow.
Entries are separated by a line '%%'; optional first lines: '@cwd <relpath>', '@list' (a JSON argv), '@tool <name>'.
Usage: python3 allowed.py <guard.py> <repo> <corpus>   (exit status 1 if any entry is blocked)"""
import json
import os
import subprocess
import sys

guard, repo, path = sys.argv[1], sys.argv[2], sys.argv[3]
entries = [e.strip("\n") for e in open(path).read().split("\n%%\n") if e.strip()]
bad = 0
for n, e in enumerate(entries, 1):
    cwd, tool, as_list = repo, "Bash", False
    lines = e.split("\n")
    while lines and lines[0].startswith("@"):
        k, _, v = lines.pop(0).partition(" ")
        if k == "@cwd":
            cwd = os.path.join(repo, v)
        elif k == "@list":
            as_list = True
        elif k == "@tool":
            tool = v
    body = "\n".join(lines)
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": json.loads(body) if as_list else body}, "cwd": cwd})
    r = subprocess.run([sys.executable, guard], input=payload, universal_newlines=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if r.returncode != 0:
        bad += 1
        print("  not allowed (exit %d): %s\n      %s" % (r.returncode, body.replace("\n", "\\n")[:160],
                                                        r.stderr.strip().replace("\n", " | ")[:300]))
print("  %d of %d allowed" % (len(entries) - bad, len(entries)))
sys.exit(1 if bad else 0)
