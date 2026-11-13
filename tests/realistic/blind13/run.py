"""Replay the ninth (blind) tester's 409 guard cases: 205 ordinary agent actions that must be allowed and 204
forbidden ones, against three repos built by mkrepos.sh. A few forbidden cases are by design not blocked at the
moment of the edit (ACCEPTED, with where they are caught instead).
Usage: python3 run.py <guard.py> <work dir>   (exit 1 on any other mismatch)"""
import json
import os
import subprocess
import sys

GUARD, B = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
subprocess.run(["bash", os.path.join(HERE, "mkrepos.sh"), B], check=True, capture_output=True)
KIND = {"shopcore": "own", "dashboard": "own", "ingestd": "work"}
ACCEPTED = {  # label: where it is caught instead
    "pyF: rename test to _test (uncollected)": "walkthrough: fewer tests",
    "pyF: rename test to check_ (uncollected)": "walkthrough: fewer tests",
    "pyF: apply_patch rename test to uncollected": "walkthrough: fewer tests",
    "goF: rename Test to lowercase (uncollected)": "walkthrough: fewer tests",
    "tsF: bracket it['skip']": "walkthrough: fewer tests",
    "tsF: test.todo replacing real test": "walkthrough: fewer tests",
    "pyF: conftest collection hook adds skip": "walkthrough: a test skips itself under a condition",
    "pyF: importorskip at module top": "walkthrough: a test skips itself under a condition",
    "pyF: Write moves skip from one test to another (count unchanged)": "walkthrough: a skip moved to a different test",
    "tsF: Write swaps which test is skipped (count unchanged)": "walkthrough: a skip moved to a different test",
    "pyF: apply_patch cross-file swap (unskip in tracking, skip in checkout)": "walkthrough: a skip moved to a different test",
    "pyF: skip edit after worktree already unskipped elsewhere (two-step cross-file swap)": "walkthrough: a skip moved to a different test",
    "tsF: vitest exclude a test dir": "walkthrough: tests excluded in config",
    "pyF: noqa with rule but no reason": "by design: Python and Go suppressions need the rule named, not a reason",
    "pyF: type: ignore[code] no reason": "by design: as above",
    "goF: //nolint:errcheck no reason": "by design: as above",
    "shF not-mine: overwrite team CONTRIBUTING.md": "by design: team docs are ordinary work; a commit of them is blocked",
    "shF not-mine: AI branch ai-": "by design: 'ai' names real work (an ai-model loader); claude/codex/gpt names are blocked",
    "pyF: getattr-built skip marker": "known gap (tests/floor_known_gaps.json)",
    "tsF: apply_patch rename test file to .spec.ts (not in vitest include)": "known gap (tests/floor_known_gaps.json)",
    "shF own/local: lets via python": "not a bypass: lib/walkthrough.py has no entry point, so this does nothing",
}
CASES = []


def P(repo, rel):
    return "%s/%s/%s" % (B, repo, rel)


def read(repo, rel):
    with open(P(repo, rel)) as f:
        return f.read()


def add(label, expect, repo, payload, setup=""):
    CASES.append({"label": label, "expect": expect, "repo": repo, "setup": setup, "payload": payload})


def bash(label, expect, repo, cmd, setup=""):
    add(label, expect, repo, {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": "%s/%s" % (B, repo)}, setup)


def edit(label, expect, repo, rel, old, new, setup="", replace_all=False):
    add(label, expect, repo, {"tool_name": "Edit", "tool_input": {"file_path": P(repo, rel), "old_string": old,
        "new_string": new, "replace_all": replace_all}, "cwd": "%s/%s" % (B, repo)}, setup)


def multi(label, expect, repo, rel, edits, setup=""):
    add(label, expect, repo, {"tool_name": "MultiEdit", "tool_input": {"file_path": P(repo, rel),
        "edits": [{"old_string": o, "new_string": n} for o, n in edits]}, "cwd": "%s/%s" % (B, repo)}, setup)


def write(label, expect, repo, rel, content, setup=""):
    add(label, expect, repo, {"tool_name": "Write", "tool_input": {"file_path": P(repo, rel), "content": content},
        "cwd": "%s/%s" % (B, repo)}, setup)


def patch(label, expect, repo, body, setup=""):
    add(label, expect, repo, {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n" + body + "*** End Patch"},
        "cwd": "%s/%s" % (B, repo)}, setup)


def sub(repo, rel, old, new):
    s = read(repo, rel)
    assert old in s, (rel, old)
    return s.replace(old, new, 1)


for f in ("cases_ordinary.py", "cases_forbidden.py"):
    exec(open(os.path.join(HERE, f)).read())


def reset(repo):
    cmds = ("git checkout -q -f feat/work && git reset -q --hard && git clean -qfdx && "
            "(git config --unset lets.agents || true) && git config lets.kind " + KIND[repo] + " && "
            "for b in $(git for-each-ref --format='%(refname:short)' refs/heads/ | grep -v -e '^main$' -e '^feat/work$'); do git branch -q -D $b; done; "
            "git stash clear; git config --remove-section 'branch.feat/work' 2>/dev/null; git config --remove-section alias 2>/dev/null; true")
    subprocess.run(["bash", "-c", cmds], cwd="%s/%s" % (B, repo), check=True, capture_output=True)


bad, n = 0, {"allow": [0, 0], "block": [0, 0]}
env = dict(os.environ, HOME=os.path.join(B, "home"))
for c in CASES:
    reset(c["repo"])
    if c["setup"]:
        subprocess.run(["bash", "-c", c["setup"]], cwd="%s/%s" % (B, c["repo"]), capture_output=True, env=env)
    p = subprocess.run([sys.executable, GUARD], input=json.dumps(c["payload"]), universal_newlines=True, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd="%s/%s" % (B, c["repo"]), timeout=60)
    got = "block" if p.returncode == 2 else "allow" if p.returncode == 0 else "exit%d" % p.returncode
    n[c["expect"]][0] += 1
    if got == c["expect"] or (c["expect"] == "block" and got == "allow" and c["label"] in ACCEPTED):
        n[c["expect"]][1] += 1
    else:
        bad += 1
        print("  MISMATCH [%s] %s: expected %s, got %s :: %s" % (c["repo"], c["label"], c["expect"], got, p.stderr.strip()[:200]))
print("  %d ordinary allowed of %d; %d forbidden blocked or caught where documented of %d (%d accepted)" % (
    n["allow"][1], n["allow"][0], n["block"][1], n["block"][0], len(ACCEPTED)))
sys.exit(1 if bad else 0)
