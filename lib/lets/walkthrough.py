"""Walkthroughs: which changed files you've already shown you understand.

A pass records the content (blob id) of each file a branch changes relative to its base. Passes are kept per
repository and keyed by path and content, not by branch, so rebasing, merging the default branch in, renaming a
branch, stacking one branch on another or a detached HEAD never costs a re-quiz: a file needs a new walkthrough
only when its content is one you haven't walked through. Files under plans/ are left out: you shaped them with the
agent in /lets:change-start, and /lets:change-close writes the spec updates after the walkthrough.

The base is, in order: what the caller passes (a PR's target branch) or `git config lets.base`, the remote's
default branch, then whichever of main, master, develop, development or trunk the branch forked from most recently,
always preferring origin's copy over a possibly stale local one.
"""

import json
import os
import re
import subprocess

EXCLUDED_PREFIXES = ("plans/",)  # planning files in the repo: you shaped them while planning
CANDIDATES = ["main", "master", "develop", "development", "trunk"]
# In a repo that isn't yours: the owners' docs and agent config, and your private files. Agents don't commit these,
# and uncommitted changes to them don't hold up a walkthrough pass (they aren't shipped).
GUEST_PROTECTED = re.compile(
    r"(^|/)(GLOSSARY(-MAP)?\.md|CONTEXT(-MAP)?\.md|CODING_STANDARDS\.md|CLAUDE(\.local)?\.md|"
    r"AGENTS\.md)$|(^|/)docs/(adr|agents)/|^(\.claude|\.agents|\.codex|openspec|plans|\.lets|\.scratch)/"
)

# A branch name, commit message or PR text that mentions an AI: kept out of every repo.
AI_NAME = re.compile(r"(^|[/_.-])(claude|codex|copilot|anthropic|chatgpt|gpt-?\d[\w.]*|gemini)([/_.-]|$)", re.I)
AI_TRACE = re.compile(
    r"co-authored-by:[^\n]*(claude|codex|anthropic|openai|copilot|noreply@)|generated (with|by) "
    r"\[?(claude|codex|chatgpt|copilot)|\U0001f916|\bclaude[- ]code\b|\bcodex\b|\bclaude\b",
    re.I,
)
RISKY = re.compile(r"\bgit\b.*\b(push|commit|merge|rebase|cherry-pick|revert|am)\b|\b(gh|glab)\b")


def _git(args, cwd, check=True):
    r = subprocess.run(["git"] + args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout.strip() if r.returncode == 0 else ""


def _merge_base(cwd, ref):
    if not _git(["rev-parse", "--verify", "--quiet", ref + "^{commit}"], cwd, check=False):
        return ""
    return _git(["merge-base", "HEAD", ref], cwd, check=False)


def base_branch(cwd):
    """(name, how it was chosen) of the branch this work merges into, or (None, why not) when it's left to detection.

    In order: this branch's own base (`lets note base`, for stacked pull requests), this repo's (`lets setup
    --base`), then the remote's default branch."""
    here = _git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd, check=False)
    if here:
        own = _git(["config", "--get", "branch.%s.lets-base" % here], cwd, check=False)
        if own:
            return own, "set for this branch"
    repo = _git(["config", "--get", "lets.base"], cwd, check=False)
    if repo:
        return repo, "set for this repo"
    remote_head = _git(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], cwd, check=False)
    if remote_head:
        return remote_head.split("/", 1)[-1], "the remote's default branch"
    return None, "whichever usual trunk this branch split from most recently"


def default_base(cwd, base=None):
    """Merge-base of HEAD with the branch this work will merge into.

    An explicit target (a PR's base, this branch's `lets note base`, or the repo's `lets.base`) wins, the remote copy
    before a possibly stale local one. Otherwise the remote's default branch, or else whichever usual trunk the
    branch forked from most recently.
    """
    here = _git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd, check=False)
    own = _git(["config", "--get", "branch.%s.lets-base" % here], cwd, check=False) if here else ""
    for name in [b for b in (base, own, _git(["config", "--get", "lets.base"], cwd, check=False)) if b]:
        for ref in ("origin/" + name, name):
            mb = _merge_base(cwd, ref)
            if mb:
                return mb
    remote_head = _git(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], cwd, check=False)
    if remote_head:
        mb = _merge_base(cwd, remote_head)
        if mb:
            return mb
    here = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd, check=False)
    best = None
    for name in CANDIDATES:
        if name == here:
            continue
        for ref in ("origin/" + name, name):
            mb = _merge_base(cwd, ref)
            if mb:
                ahead = int(_git(["rev-list", "--count", mb + "..HEAD"], cwd, check=False) or 0)
                if best is None or ahead < best[0]:
                    best = (ahead, mb)
                break
    if best:
        return best[1]
    return _git(["rev-list", "--max-parents=0", "HEAD"], cwd).splitlines()[0]


def changed_files(cwd, base=None):
    base = default_base(cwd, base)
    names = _git(["diff", "--name-only", "--no-renames", base, "HEAD"], cwd).splitlines()
    return base, [n for n in names if n and not n.startswith(EXCLUDED_PREFIXES)]


def _blob(cwd, path):
    return _git(["rev-parse", "--verify", "--quiet", "HEAD:" + path], cwd, check=False) or "deleted"


def _record_file(cwd):
    common = _git(["rev-parse", "--git-common-dir"], cwd)
    common = common if os.path.isabs(common) else os.path.join(cwd, common)
    return os.path.join(common, "lets", "walkthrough", "passed.json")


def _load(cwd):
    try:
        with open(_record_file(cwd)) as f:
            data = json.load(f)
        return {k: set(v) for k, v in data.items()}
    except (OSError, ValueError, AttributeError):
        return {}


def scope(cwd, base=None):
    """(base, committed files on this branch whose current content you haven't passed)."""
    base, files = changed_files(cwd, base)
    done = _load(cwd)
    return base, [p for p in files if _blob(cwd, p) not in done.get(p, set())]


def questions(cwd, base=None):
    """Changes on this branch that loosen a check and need your judgement (the floor guard's findings that don't
    block a commit, such as fewer tests or a config exclusion), in files you haven't passed yet."""
    from . import floor as floor_guard

    base, todo = scope(cwd, base)
    if not todo:
        return []
    found = [f for f in floor_guard.check([base, "HEAD"], cwd) if not floor_guard.blocking(f)]
    return [f for f in found if f[0].startswith("(") or f[0] in todo]


def is_guest(cwd):
    """True unless `lets setup` marked this repo as yours (`lets.kind own`). Every other repo (work, open source,
    clients, friends) keeps everything agent-related local, and so does a repo nobody has set up yet."""
    return _git(["config", "--get", "lets.kind"], cwd, check=False) != "own"


AGENT_LEVELS = ("local", "commit", "ship")


def agent_level(cwd):
    """What agents may do with git here: `local` (the default: edit, branch, stash; you commit and push), `commit`
    (also commit to feature branches) or `ship` (also push feature branches and open PRs)."""
    level = _git(["config", "--get", "lets.agents"], cwd, check=False)
    return level if level in AGENT_LEVELS else "local"


def uncommitted(cwd):
    """Tracked files with changes not yet committed (in a guest repo, not counting the team's docs)."""
    names = _git(["diff", "--name-only", "HEAD"], cwd, check=False).splitlines()
    guest = is_guest(cwd)
    return [n for n in names if n and not (guest and GUEST_PROTECTED.search(n))]


def record_pass(cwd, base=None):
    """Record a pass for the content of the branch's committed changes. Uncommitted work isn't covered: once it is
    committed, its new content needs its own pass."""
    _base, files = changed_files(cwd, base)
    done = _load(cwd)
    for p in files:
        done.setdefault(p, set()).add(_blob(cwd, p))
    path = _record_file(cwd)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({k: sorted(v) for k, v in sorted(done.items())}, f, indent=1)
    return files


def gate_off(cwd):
    return _git(["config", "--get", "lets.walkthrough"], cwd, check=False) == "off"
