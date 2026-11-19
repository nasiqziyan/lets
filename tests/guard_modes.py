"""The guard's answers when it's unsure, when it crashes, and what a block shows. Prints one line per failed check."""
import io
import json
import os
import subprocess
import sys

REPO, CWD = sys.argv[1], sys.argv[2]
GUARD = os.path.join(REPO, "agent-hooks", "guard.py")
bad = []


def call(cmd, claude, strict=False):
    env = dict(os.environ)
    env.pop("LETS_GUARD_STRICT", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if claude:
        env["CLAUDE_PROJECT_DIR"] = CWD
    data = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": CWD})
    r = subprocess.run([sys.executable, GUARD], input=data, text=True, capture_output=True, env=env, cwd=CWD)
    return r.returncode, r.stdout, r.stderr


code, out, err = call('eval "git push origin work"', claude=True)
try:
    d = json.loads(out)["hookSpecificOutput"]
    if code != 0 or d["permissionDecision"] != "ask" or "pushes to a remote" not in d["permissionDecisionReason"]:
        bad.append("Claude Code: an unsure push asks, saying it pushes (got %s %s)" % (code, out))
except Exception:
    bad.append("Claude Code: an unsure push asks (got %s %r %r)" % (code, out, err))

code, out, err = call('eval "git push origin work"', claude=False)
if code != 2 or 'eval "git push origin work"' not in err:
    bad.append("Codex: an unsure push is blocked and the message shows the command (got %s %r)" % (code, err))

code, out, err = call("git reset --hard", claude=True)
if code != 2 or "\ngit reset --hard\n" not in err or "type ! and paste" not in err:
    bad.append("a block shows the exact command to run yourself (got %s %r)" % (code, err))

# A crash inside the guard: a harmless command runs, a risky one asks (Claude Code) or is blocked (Codex).
sys.path.insert(0, os.path.join(REPO, "lib"))
from lets import guard  # noqa: E402


def boom(*a, **k):
    raise TypeError("simulated")


guard.check_shell = boom
os.environ.pop("LETS_GUARD_STRICT", None)
for cmd, claude, want in (("git branch --contains abc", False, 0), ("git push", True, "ask"), ("git push", False, 2)):
    CLAUDE = os.environ.pop("CLAUDE_PROJECT_DIR", None)
    if claude:
        os.environ["CLAUDE_PROJECT_DIR"] = CWD
    sys.stdin = io.StringIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": CWD}))
    out, err = io.StringIO(), io.StringIO()
    sys.stdout, sys.stderr = out, err
    try:
        guard.CALL["cmd"] = None
        guard.entry()
        got = 0
    except SystemExit as e:
        got = e.code or 0
    sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
    if want == "ask":
        ok = got == 0 and '"ask"' in out.getvalue()
    else:
        ok = got == want and (want != 0 or not out.getvalue())
    if not ok:
        bad.append("guard crash on %r (claude=%s): want %s, got %s %r" % (cmd, claude, want, got, err.getvalue()))

log = os.path.join(os.environ["XDG_CACHE_HOME"], "lets", "guard.log")
kinds = [json.loads(l)["kind"] for l in open(log)] if os.path.exists(log) else []
if not {"block", "ask", "crash"} <= set(kinds):
    bad.append("the guard logs blocks, prompts and crashes (got %s)" % sorted(set(kinds)))
print("\n".join(bad))
