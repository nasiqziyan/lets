"""`lets changes`: where each change stands, from local files and, when it can, GitLab or GitHub (read only).

A change is open until it is archived. An archived change is merged only when that's known: with plans in the code
repo, its archive arrived through the base branch; with a planning repo, `x-lets-merged` records the merge. Dropped
changes say so in their proposal. Nothing here writes to GitLab or GitHub, and nothing polls: commands ask when they
need to know.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

from .core import LetsError, git, say
from .paths import expand

STATES = {
    "open": "open",
    "merged": "merged",
    "approved": "approved, not merged",
    "review": "in review",
    "closed": "pull request closed without merging",
    "dropped": "dropped",
    "unconfirmed": "closed, merge not confirmed",
    "none": "no pull request yet",
    "unknown": "GitLab/GitHub couldn't be read",
    "ambiguous": "several pull requests match",
}


def label(folder: pathlib.Path, key: str) -> str:
    f = folder / ".openspec.yaml"
    hit = re.search(r"^%s:\s*(\S+)" % re.escape(key), f.read_text(), re.M) if f.exists() else None
    return hit.group(1).strip("'\"") if hit else ""


def set_label(folder: pathlib.Path, key: str, value: str) -> None:
    """Add or replace one `x-lets-*` line in a change's .openspec.yaml (OpenSpec ignores keys starting `x-`)."""
    f = folder / ".openspec.yaml"
    text = f.read_text() if f.exists() else ""
    line = "%s: %s" % (key, value)
    if re.search(r"^%s:" % re.escape(key), text, re.M):
        text = re.sub(r"^%s:.*$" % re.escape(key), line, text, flags=re.M)
    else:
        text = text + ("" if not text or text.endswith("\n") else "\n") + line + "\n"
    f.write_text(text)


def tasks_done(folder: pathlib.Path) -> tuple[int, int]:
    f = folder / "tasks.md"
    text = f.read_text() if f.exists() else ""
    groups = re.split(r"^##\s+", text, flags=re.M)[1:]
    done = sum(1 for g in groups if re.search(r"^\s*- \[[xX]\]", g, re.M) and not re.search(r"^\s*- \[ \]", g, re.M))
    return done, len(groups)


def archived_folder(proot: pathlib.Path, name: str) -> pathlib.Path | None:
    d = proot / "openspec" / "changes" / "archive"
    if not d.exists():
        return None
    hits = sorted(p for p in d.iterdir() if re.match(r"^\d{4}-\d{2}-\d{2}-%s$" % re.escape(name), p.name))
    return hits[-1] if hits else None


def dropped(folder: pathlib.Path) -> bool:
    p = folder / "proposal.md"
    return p.exists() and bool(re.search(r"^##\s+Dropped\b", p.read_text(), re.M))


def in_repo(proot: pathlib.Path) -> bool:
    """Plans kept in the code repo's own plans/ folder (not a separate planning repo)."""
    return proot.name == "plans" and (proot.parent / ".git").exists()


def local_outcome(proot: pathlib.Path, name: str, here_branch: str = "") -> str:
    """What local files alone say about a change: open, merged, dropped or unconfirmed (no network)."""
    if (proot / "openspec" / "changes" / name).is_dir():
        return "open"
    arch = archived_folder(proot, name)
    if arch is None:
        return "open"
    if dropped(arch):
        return "dropped"
    if label(arch, "x-lets-merged"):
        return "merged"
    if in_repo(proot):
        # its archive came here through the base branch, unless this is the change's own branch, closed before approval
        return "unconfirmed" if label(arch, "x-lets-branch") == here_branch and here_branch else "merged"
    return "unconfirmed"


# ---------- GitLab / GitHub, read only ----------


def forge_of(repo: pathlib.Path) -> str:
    url = git("remote", "get-url", "origin", cwd=repo, check=False) or ""
    return "gh" if "github.com" in url else "glab" if url else ""


def _json(cmd: list[str], cwd: pathlib.Path) -> object | None:
    try:
        r = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout or "null")
    except ValueError:
        return None


def requests_for(repo: pathlib.Path, branch: str) -> list[dict] | None:
    """Pull or merge requests from `branch`, in any state: [{url, state, target}]. None if they can't be read."""
    tool = forge_of(repo)
    if tool == "gh":
        data = _json(
            [
                "gh",
                "pr",
                "list",
                "--head",
                branch,
                "--state",
                "all",
                "--limit",
                "20",
                "--json",
                "url,state,baseRefName,reviewDecision",
            ],
            repo,
        )
        if not isinstance(data, list):
            return None
        out = []
        for d in data:
            st = {"MERGED": "merged", "CLOSED": "closed"}.get(d.get("state", ""), "review")
            if st == "review" and d.get("reviewDecision") == "APPROVED":
                st = "approved"
            out.append({"url": d.get("url", ""), "state": st, "target": d.get("baseRefName", "")})
        return out
    if tool == "glab":
        data = _json(["glab", "mr", "list", "--source-branch", branch, "--all", "--per-page", "20", "-F", "json"], repo)
        if not isinstance(data, list):
            return None
        out = []
        for d in data:
            st = {"merged": "merged", "closed": "closed", "locked": "closed"}.get(d.get("state", ""), "review")
            if st == "review" and (d.get("detailed_merge_status") == "mergeable" or d.get("approved") is True):
                st = "approved"
            out.append({"url": d.get("web_url", ""), "state": st, "target": d.get("target_branch", "")})
        return out
    return None


def request_state(repo: pathlib.Path, branch: str, recorded: str = "") -> dict:
    """The one request for this change: the recorded link if there is one, else the only match (a merged one wins,
    then an open one). {state, url, target, others}."""
    found = requests_for(repo, branch)
    if found is None:
        return {"state": "unknown", "url": recorded, "target": "", "others": []}
    if recorded:
        same = [r for r in found if r["url"] == recorded]
        if same:
            return {**same[0], "others": []}
    if not found:
        return {"state": "none", "url": "", "target": "", "others": []}
    for want in ("merged", "approved", "review"):
        hits = [r for r in found if r["state"] == want]
        if len(hits) == 1:
            return {**hits[0], "others": []}
        if len(hits) > 1:
            return {"state": "ambiguous", "url": "", "target": "", "others": [r["url"] for r in hits]}
    return {**found[0], "others": []}


# ---------- which changes, and where ----------


def code_repo_for(proot: pathlib.Path, folder: pathlib.Path, here: pathlib.Path) -> pathlib.Path:
    if in_repo(proot):
        return proot.parent
    name = label(folder, "x-lets-repo")
    if name:
        path = git("config", "--get", "letsrepo.%s.path" % name, cwd=proot, check=False)
        if path:
            return expand(path)
    return here


def branch_for(code_repo: pathlib.Path, folder: pathlib.Path, name: str) -> str:
    """The change's branch: recorded on the change (it outlives a deleted branch), else this repo's branch notes."""
    recorded = label(folder, "x-lets-branch")
    if recorded:
        return recorded
    raw = git("config", "--get-regexp", r"^branch\..*\.lets-change$", cwd=code_repo, check=False) or ""
    for line in raw.splitlines():
        key, _, value = line.partition(" ")
        if value.strip() == name:
            return key[len("branch.") : -len(".lets-change")]
    return ""


def branch_changes(repo: pathlib.Path, current: str) -> list[dict]:
    """Plans in the code repo: open changes that exist only on other local branches (read with git, nothing switched)."""
    out = []
    refs = git("for-each-ref", "--format=%(refname:short)", "refs/heads", cwd=repo, check=False) or ""
    here = repo / "plans" / "openspec" / "changes"
    for b in refs.splitlines():
        if b == current:
            continue
        names = git("ls-tree", "-d", "--name-only", "%s:plans/openspec/changes" % b, cwd=repo, check=False) or ""
        for n in names.splitlines():
            if n == "archive" or (here / n).is_dir() or archived_folder(repo / "plans", n):
                continue
            tasks = git("show", "%s:plans/openspec/changes/%s/tasks.md" % (b, n), cwd=repo, check=False) or ""
            groups = re.split(r"^##\s+", tasks, flags=re.M)[1:]
            done = sum(1 for g in groups if "- [x]" in g.lower() and "- [ ]" not in g)
            out.append({"change": n, "where": "branch %s" % b, "branch": b, "done": done, "total": len(groups)})
    return out


def gather(here: pathlib.Path, only: str = "", online: bool = True) -> list[dict]:
    from .planning import planning_root

    proot, _home = planning_root(here)
    if proot is None:
        raise LetsError("This repo isn't set up for LETS: run `lets setup` here.")
    current = git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=here, check=False) or ""
    rows = []
    changes = proot / "openspec" / "changes"
    names = sorted(p.name for p in changes.iterdir() if p.is_dir() and p.name != "archive") if changes.exists() else []
    if only:
        names = [only] if only in names else []
    for n in names:
        folder = changes / n
        repo = code_repo_for(proot, folder, here)
        branch = branch_for(repo, folder, n)
        done, total = tasks_done(folder)
        row = {"change": n, "where": "here", "branch": branch, "done": done, "total": total, "state": "open"}
        if online and branch:
            req = request_state(repo, branch, label(folder, "x-lets-request"))
            row.update(state=req["state"], request=req["url"], target=req["target"], others=req["others"])
        elif not branch:
            row["state"] = "none"
        rows.append(row)
    if in_repo(proot) and not only:
        for r in branch_changes(proot.parent, current):
            r["state"] = "open"
            rows.append(r)
    if only and not rows:
        arch = archived_folder(proot, only)
        if arch is None:
            raise LetsError("There's no change called %s here." % only)
        rows.append({"change": only, "where": "archive", "state": local_outcome(proot, only, current)})
    return rows


def cmd_changes(a) -> None:
    rows = gather(pathlib.Path.cwd(), a.change or "", online=not a.offline)
    if a.json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        say("No open changes.")
    for r in rows:
        state = str(r.get("state", ""))
        bits: list[str] = [STATES.get(state, state)]
        if r.get("total"):
            bits.append("tasks %d of %d" % (r["done"], r["total"]))
        if r.get("branch"):
            bits.append("branch %s" % r["branch"])
        if r.get("target") and r.get("state") == "merged":
            bits.append("into %s" % r["target"])
        if r.get("where", "here") not in ("here", "archive"):
            bits.append("found on %s only" % r["where"].split(" ", 1)[1])
        say("%s: %s" % (r["change"], " · ".join(bits)))
        if r.get("request"):
            say("    %s" % r["request"])
        for o in r.get("others", []):
            say("    could be %s" % o)
