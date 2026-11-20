#!/usr/bin/env python3
# pyright: reportOptionalSubscript=false, reportOptionalIterable=false, reportArgumentType=false, reportOperatorIssue=false
# (the parser narrows its optional values with checks pyright cannot follow)
"""PreToolUse guard for Claude Code and Codex. The gates bind the agents; you stay free to act yourself.

For every shell command or file edit an agent makes, it:
1. Blocks commands that would bypass or change the gates (including `lets` commands only you run), edits inside
   .git/ or to git's config files, and commands that throw away uncommitted work across the whole tree.
2. Checks every file edit as it is made: an edit that adds a blocking floor-guard finding (a new skip, focus or
   unexplained suppression) is refused before it lands. A finding you approve for the branch (`git config --add
   branch.<name>.letsAllow '<finding>'`, printed in the block message) no longer blocks there.
3. Keeps git local by default (`lets.agents`): agents edit, branch and stash, and you commit and push. Where you
   allow `commit`, a commit runs the floor guard on what is being committed (replaying any `git add` earlier in the
   same command) and the repo's fast check (`lets.check`). Where you allow `ship`, an agent may also push a feature
   branch and open a PR, once the whole branch has no blocking finding and you've completed a walkthrough of it. In
   your private planning repo (`lets.role planning`), agents commit on its main branch, and never push.
4. Never lets an agent merge or approve a PR/MR, use --admin, or push to a shared branch: those are a person's job.
5. Keeps AI mentions out of every repo, planning repos included: no branch name, commit message or PR/MR title or
   description that names an AI or carries an AI trailer.
6. Where the team hasn't agreed to agents (anything without `lets.kind own`, which includes repos you haven't set up):
   agents read anything but change nothing the team sees: gh and glab only to read (a repo named with -R counts too),
   and no commits of the owners' docs, agent config or planning files.

It is a tripwire, not a sandbox: it reads commands as text, so a determined agent could find another route (a
file written by a shell command isn't checked until it's committed). CI, protected branches and a human reviewer
stay the final gates. Exit 2 blocks the call in both tools (stderr goes to the agent), and every block shows the
exact command so I can run it myself. A command that commits, pushes or opens a PR and can't be checked asks me in
Claude Code (a permission prompt saying what I'd allow) and is blocked in Codex, which can't ask. If the guard itself
fails, the crash is logged for `lets doctor`; a harmless command runs, and a risky one is treated as unchecked
(`entry`). LETS_GUARD_STRICT=1 shows the full error instead.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

SHARED_NAMES = {"main", "master", "trunk", "develop", "development", "release"}
WRITE_VERB = (
    r"(?:(?:^|\s)(?:touch|tee|cp|mv|rm|mkdir|ln|install|truncate|dd|chmod|chown|sed\s+-i\w*)\s|>|"
    r"(?:^|\s)(?:python3?|node|ruby|perl)\s+-[ce]\s.*(?:open|write|unlink|rename))"
)
GIT_CONFIG_FILES = r"(\.git/(config|hooks|info/exclude)\b|\.gitconfig\b|\.config/git/(config|ignore)\b)"
# Raw-text tripwires, matched on the command as written and with quotes removed.
BYPASS = [
    (r"\bgit\b.*\s--no-v[a-z-]*", "skips git hooks (--no-verify)"),
    (
        r"(-c\s*|--config-env[= ])core\.hooksPath|GIT_CONFIG_(KEY|VALUE|COUNT|PARAMETERS)|GIT_CONFIG_GLOBAL|"
        r"GIT_CONFIG_SYSTEM",
        "changes where git hooks or settings come from",
    ),
    (
        r"(^|\s)(HUSKY|LEFTHOOK)=0\b|(^|\s)SKIP=\S|PRE_COMMIT_ALLOW_NO_CONFIG|\b(pre-commit|husky|lefthook)\s+uninstall\b",
        "switches off the repo's hook manager",
    ),
    (r"\bFLOOR_GUARD_ALLOW\s*=", "overrides the floor guard"),
    (
        r"\brecord_pass\s*\(|(^|[\s/])lets(\.py)?\s+walkthrough\s+['\"]?(pass|complete)\b|"
        + WRITE_VERB
        + r".*(\.git/|/)lets/walkthrough\b",
        "records a walkthrough as complete (only you do that)",
    ),
    (WRITE_VERB + r".*" + GIT_CONFIG_FILES, "edits git configuration or hooks"),
]
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch"}
GIT_OPTS_WITH_VALUE = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--exec-path",
    "--config-env",
    "--super-prefix",
    "--attr-source",
}
COMMIT_OPTS_WITH_VALUE = {
    "-m",
    "--message",
    "-F",
    "--file",
    "-C",
    "--reuse-message",
    "-c",
    "--reedit-message",
    "--fixup",
    "--squash",
    "--author",
    "--date",
    "-t",
    "--template",
    "--cleanup",
    "--trailer",
    "--pathspec-from-file",
}
PREFIX_WORDS = {
    "command",
    "exec",
    "time",
    "nohup",
    "then",
    "do",
    "else",
    "if",
    "while",
    "until",
    "!",
    "(",
    "{",
    "chronic",
    "caffeinate",
}
# Wrappers that run another program, with the options of theirs that take a value.
WRAPPERS = {
    "env": {"-u", "--unset", "-C", "--chdir", "-S"},
    "sudo": {"-u", "-g", "-h", "-p", "-C"},
    "nice": {"-n", "--adjustment"},
    "ionice": {"-c", "-n", "-p"},
    "stdbuf": {"-i", "-o", "-e"},
    "timeout": {"-s", "--signal", "-k", "--kill-after"},
    "xargs": {"-n", "-P", "-I", "-L", "-d", "-a", "-s"},
}
READ_ONLY = {
    "echo",
    "printf",
    "grep",
    "egrep",
    "rg",
    "ag",
    "cat",
    "less",
    "more",
    "head",
    "tail",
    "man",
    "which",
    "type",
    "help",
    "wc",
    "sort",
    "uniq",
    "jq",
    "sed",
    "awk",
}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
LETS_AGENT_OK = {
    "check",
    "where",
    "sync",
    "note",
    "statusline",
    "--version",
    "-h",
    "--help",
}  # and the read-only forms below
RISKY = re.compile(r"\bgit\b.*\b(push|commit|merge|rebase|cherry-pick|revert|am|pull)\b|\b(gh|glab)\b")


class Unchecked(Exception):
    """A command that ships or commits, in a form the guard can't follow."""


CALL = {"cmd": None}  # the shell command being checked, for messages and the log


def in_claude_code():
    """Claude Code sets CLAUDE_PROJECT_DIR for its hooks; Codex doesn't, and has no "ask" answer."""
    return bool(os.environ.get("CLAUDE_PROJECT_DIR"))


def log(kind, why):
    """Keep the last 200 blocks, prompts and crashes, for `lets guard log` and `lets doctor`."""
    try:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
        path = os.path.join(base, "lets", "guard.log")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        lines = []
        if os.path.exists(path):
            with open(path) as f:
                lines = f.read().splitlines()[-199:]
        import time

        entry = {"time": int(time.time()), "kind": kind, "why": why, "command": (CALL["cmd"] or "")[:500]}
        with open(path, "w") as f:
            f.write("\n".join(lines + [json.dumps(entry)]) + "\n")
    except Exception:  # noqa: BLE001  the log never gets in the way
        pass


def effect(cmd):
    """What a command does that the guard cares about, in plain words."""
    found = []
    for rx, words in (
        (r"\bgit\b.*\bcommit\b", "makes a commit"),
        (r"\bgit\b.*\bpush\b", "pushes to a remote"),
        (r"\bgit\b.*\b(merge|rebase|cherry-pick|revert|am|pull)\b", "changes a branch's history"),
        (r"\b(gh|glab)\b", "runs gh or glab against GitHub or GitLab"),
    ):
        if re.search(rx, cmd or ""):
            found.append(words)
    return ", ".join(found) or "changes files or settings"


def block(why):
    log("block", why)
    msg = "Blocked by the LETS guard: %s\n" % why
    if CALL["cmd"]:
        msg += (
            "Don't try another way round it. Tell me what was blocked and why, and show me this command exactly, in a "
            "code block, so I can run it myself if I choose (in Claude Code I type ! and paste it; or in a terminal):"
            "\n\n%s\n" % CALL["cmd"]
        )
    else:
        msg += "Don't try another way round it. Tell me what was blocked and why; I can make the change myself.\n"
    sys.stderr.write(msg)
    sys.exit(2)


def unsure(why):
    """The guard can't check this call. Claude Code asks me, showing what I'd allow; Codex can't ask, so it blocks."""
    if not in_claude_code():
        block("it couldn't check this call: %s" % why)
    log("ask", why)
    reason = "LETS couldn't check this: %s. If you allow it, it runs exactly as shown and %s." % (
        why.rstrip("."),
        effect(CALL["cmd"]),
    )
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def run(args, cwd, timeout=None, env=None):
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        env=env,
    )


def git_out(args, cwd, env=None):
    r = run(["git"] + args, cwd, env=env)
    return r.stdout.strip() if r.returncode == 0 else ""


def segments(cmd):
    cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?\n.*?\n\1\b", " ", cmd, flags=re.S)  # heredoc bodies (messages)
    # Quoted messages, titles and bodies: their words are prose, not commands.
    cmd = re.sub(
        r"(\s(?:-[a-zA-Z]*m|--message|--body|-b|--title|-t|--description)(?:=|\s+))"
        r"(\"(?:[^\"\\]|\\.)*\"|'[^']*')",
        r"\1''",
        cmd,
    )
    return [s.strip() for s in re.split(r"&&|\|\||;|\||\n", cmd) if s.strip()]


def tokens(seg):
    try:
        toks = shlex.split(seg, comments=True)
    except ValueError:  # unbalanced quotes: fall back to words, never to "allow"
        toks = [w.strip("'\"") for w in seg.split()]
    while toks:
        if toks[0] in PREFIX_WORDS or re.match(r"^\w+=", toks[0]):
            toks = toks[1:]
        elif os.path.basename(toks[0]) in WRAPPERS:
            takes, i = WRAPPERS[os.path.basename(toks[0])], 1
            while i < len(toks) and (toks[i].startswith("-") or re.match(r"^\w+=", toks[i])):
                i += 2 if toks[i] in takes else 1
            if os.path.basename(toks[0]) == "timeout" and i < len(toks):
                i += 1  # the duration
            toks = toks[i:]
        else:
            break
    if toks:  # (git push ...) and { git push ...; }
        toks[0] = toks[0].lstrip("({")
        while toks[-1][-1:] in (")", "}") and toks[-1].count(toks[-1][-1]) > toks[-1].count(
            "(" if toks[-1][-1] == ")" else "{"
        ):
            toks[-1] = toks[-1][:-1]  # a closing subshell or group, not the end of a $(...)
    return [t for t in toks if t]


def parse_tool(toks, name):
    """(index of the program token, args) for git, gh or glab: the program itself, or run by another program
    (xargs, ssh, a script runner), unless the first program only prints or searches text."""
    if not toks or os.path.basename(toks[0]) in READ_ONLY:
        return None, None
    for i, t in enumerate(toks):
        if os.path.basename(t) == name:
            return i, toks[i + 1 :]
    return None, None


def resolve_dir(base, target):
    """Where a `cd` or `git -C` lands, or None when the guard can't tell."""
    if base is None:
        return None
    if re.search(r"rev-parse\s+--show-toplevel", target):
        return git_out(["rev-parse", "--show-toplevel"], base) or None
    if "$" in target or "`" in target:
        return None
    path = os.path.normpath(os.path.join(base, os.path.expanduser(target)))
    return path if os.path.isdir(path) else None


def parse_git(toks, cwd):
    """(subcommand, args, repo dir) for a git command, else (None, None, cwd)."""
    i, rest = parse_tool(toks, "git")
    if i is None:
        return None, None, cwd
    where, j = cwd, 0
    while j < len(rest) and rest[j].startswith("-"):
        t = rest[j]
        if t == "-C" and j + 1 < len(rest):
            where = resolve_dir(where, rest[j + 1])
        j += 2 if t in GIT_OPTS_WITH_VALUE else 1
    return (rest[j], rest[j + 1 :], where) if j < len(rest) else (None, None, where)


def shared_branch(name, cwd):
    name = re.sub(r"^refs/heads/", "", name)
    if name in SHARED_NAMES or "*" in name:
        return True
    default = git_out(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], cwd)
    if default and name == default.split("/", 1)[-1]:
        return True
    return name in git_out(["config", "--get", "lets.shared"], cwd).split()


CONFIG_READS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l", "--show-origin", "get", "list"}


def gate_setting(args):
    """A `git config` that writes lets.* or a branch's letsAllow approvals, or removes or renames the lets section."""
    if any(a in CONFIG_READS for a in args):
        return False
    low = [a.lower() for a in args]
    if any(a.startswith(("lets.", "alias.")) or re.match(r"branch\..+\.(letsallow|lets-walked)$", a) for a in low):
        return True
    return any(a in ("--remove-section", "--rename-section", "remove-section", "rename-section") for a in low) and any(
        a == "lets" for a in low
    )


def current_branch(cwd):
    return git_out(["rev-parse", "--abbrev-ref", "HEAD"], cwd) or "HEAD"


def push_targets(args, cwd):
    """Branch names a `git push` would update, resolved through git. None means 'treat as shared'."""
    if any(a in ("--all", "--mirror", "--branches") for a in args):
        return None
    pos, skip, remote_given = [], False, False
    for a in args:
        if skip:
            skip = False
        elif a in ("-o", "--push-option", "--receive-pack", "--exec", "--repo"):
            skip = True
            remote_given = remote_given or a == "--repo"
        elif a.startswith("--repo="):
            remote_given = True
        elif not a.startswith("-"):
            pos.append(a)
    refspecs = pos if remote_given else pos[1:]
    if not refspecs:
        return [] if "--tags" in args else [current_branch(cwd)]
    out = []
    for r in refspecs:
        r = r.lstrip("+")
        if re.fullmatch(
            r"\$\((git branch --show-current|git rev-parse --abbrev-ref HEAD|git symbolic-ref --short HEAD)\)", r
        ):
            r = current_branch(cwd)
        elif "$" in r or "`" in r:
            raise Unchecked("its target branch is a shell expression")
        if r in (":", ""):
            return None
        dst = r.split(":", 1)[1] if ":" in r else r
        if dst in ("HEAD", "@") or (":" not in r and r in ("HEAD", "@")):
            dst = current_branch(cwd)
        out.append(dst)
    return out


def push_options(args):
    opts = []
    for k, a in enumerate(args):
        if a in ("-o", "--push-option") and k + 1 < len(args):
            opts.append(args[k + 1])
        elif a.startswith("--push-option="):
            opts.append(a.split("=", 1)[1])
    return opts


def on_git_push(args, cwd):
    targets = push_targets(args, cwd)
    if targets is None or any(shared_branch(t, cwd) for t in targets):
        block(
            "agents don't push to a shared branch (%s): push a feature branch and open a PR, or push it yourself"
            % (", ".join(targets) if targets else "all or wildcard branches")
        )
    opts = push_options(args)
    if any(o.startswith(("merge_request.merge_when_pipeline_succeeds", "merge_request.auto_merge")) for o in opts):
        block("agents don't merge; a person merges after review")
    if any(o.startswith("merge_request.create") for o in opts):
        target = next((o.split("=", 1)[1] for o in opts if o.startswith("merge_request.target=")), None)
        on_ship(cwd, target)


def commit_diff_args(args):
    """Which diff a commit takes: the index, or (with -a/-o/-i/pathspecs) tracked changes against HEAD."""
    skip, paths = False, False
    for k, a in enumerate(args):
        if skip:
            skip = False
            continue
        if a == "--":
            paths = paths or k + 1 < len(args)
            break
        if a in COMMIT_OPTS_WITH_VALUE:
            skip = True
            continue
        if a.startswith("--"):
            if a in ("--all", "--only", "--include", "--interactive", "--patch"):
                return ["HEAD"]
            continue
        if a.startswith("-") and len(a) > 1:
            letters = a[1:]
            if set("aoip") & set(letters.split("m")[0].split("F")[0]):
                return ["HEAD"]
            if letters[-1] in "mFCct":
                skip = True
            continue
        paths = True
    return ["HEAD"] if paths else ["--cached"]


def staged_env(root, adds):
    """An environment whose index includes the `git add`/`rm`/`mv` calls made earlier in the same command."""
    if not adds:
        return None, None
    index = git_out(["rev-parse", "--git-path", "index"], root)
    index = index if os.path.isabs(index) else os.path.join(root, index)
    fd, tmp = tempfile.mkstemp(prefix="lets-index-")
    os.close(fd)
    if os.path.exists(index):
        shutil.copyfile(index, tmp)
    else:
        os.remove(tmp)
    env = dict(os.environ, GIT_INDEX_FILE=tmp)
    for sub, args, where in adds:
        if sub == "unknown":
            raise Unchecked("it commits files chosen by another command")
        args = [a for a in args if a not in ("-i", "--interactive", "-p", "--patch", "-e", "--edit")]
        run(["git", sub] + args, where or root, env=env)  # a failing add changes nothing; the commit is checked as is
    return env, tmp


def unapproved(found, root):
    """Findings you haven't approved for this branch. Approvals live in the branch's own git config, so they end
    when the branch is deleted, and agents can't write them."""
    branch = current_branch(root)
    if branch == "HEAD":
        return found
    allowed = set(git_out(["config", "--get-all", "branch.%s.letsallow" % branch], root).splitlines())
    return [f for f in found if "%s: %s" % f not in allowed]


def explain(found, root):
    lines = "\n".join("  %s: %s" % f for f in found)
    branch = current_branch(root)
    if branch == "HEAD":
        return lines + "\nStop and show me this."
    return (
        lines + "\nStop and show me this. If I decide a finding is fine, I approve it for this branch and you "
        "retry:\n"
        + "\n".join(
            "  ! git config --add %s %s" % (shlex.quote("branch.%s.letsAllow" % branch), shlex.quote("%s: %s" % f))
            for f in found[:6]
        )
    )


def on_commit(diff_args, cwd, adds=()):
    from . import floor as floor_guard
    from . import walkthrough

    root = git_out(["rev-parse", "--show-toplevel"], cwd)
    if not root:
        return
    env, tmp = staged_env(
        root,
        [a for a in adds if a[2] and (a[0] == "unknown" or git_out(["rev-parse", "--show-toplevel"], a[2]) == root)],
    )
    try:
        git_dir = git_out(["rev-parse", "--git-dir"], root)
        if os.path.exists(os.path.join(root, git_dir, "MERGE_HEAD")):
            # A merge: flag only what is new relative to both parents, so the incoming branch isn't charged to you.
            mine = floor_guard.check(["--cached"], root, env)
            theirs = set(floor_guard.check(["--cached", "MERGE_HEAD"], root, env))
            found = [f for f in mine if f in theirs]
        else:
            if diff_args == ["HEAD"] and not git_out(["rev-parse", "--verify", "--quiet", "HEAD"], root):
                diff_args = ["--cached"]  # first commit: nothing to compare the working tree with
            found = floor_guard.check(diff_args, root, env)
        found = unapproved([f for f in found if floor_guard.blocking(f)], root)
        if found:
            block("this commit weakens a quality gate:\n" + explain(found, root))
        if walkthrough.is_guest(root):
            names = git_out(["diff", "--name-only"] + diff_args, root, env).splitlines()
            touched = [n for n in names if walkthrough.GUEST_PROTECTED.search(n)]
            if touched:
                block(
                    "The team hasn't agreed to agents working in this repo, and this commit includes the team's docs or agent config, or "
                    "planning files (%s). Those need the team's agreement; my planning lives in my planning repo"
                    % ", ".join(touched[:8])
                )
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
    check = git_out(["config", "--get", "lets.check"], root)
    if check:
        try:
            res = run(["sh", "-c", check], root, timeout=540)  # under both harnesses' hook timeouts
        except subprocess.TimeoutExpired:
            block(
                "the repo's check (%s) took over 9 minutes; I can set a faster one with `git config lets.check`" % check
            )
        if res.returncode != 0:
            block("the repo's check failed (%s):\n%s" % (check, "\n".join(res.stdout.splitlines()[-30:])))


def on_ship(cwd, base=None):
    from . import floor as floor_guard
    from . import walkthrough

    root = git_out(["rev-parse", "--show-toplevel"], cwd)
    if not root:
        return
    base = walkthrough.default_base(root, base)
    gate_off = walkthrough.gate_off(root)
    found = unapproved(
        [f for f in floor_guard.check([base, "HEAD"], root) if gate_off or floor_guard.blocking(f)], root
    )
    if found:
        block("this branch weakens a quality gate:\n" + explain(found, root))
    if gate_off:
        return
    _base, todo = walkthrough.scope(root, base)
    if todo:
        block(
            "these changed files haven't been walked through yet: %s. Run /lets:walkthrough with me; I record it as "
            "complete myself afterwards."
            % ", ".join(todo[:12])
            + (" (and %d more)" % (len(todo) - 12) if len(todo) > 12 else "")
        )


def option_value(args, names):
    for k, a in enumerate(args):
        for n in names:
            if a == n and k + 1 < len(args):
                return args[k + 1]
            if a.startswith(n + "="):
                return a.split("=", 1)[1]
    return None


FORGE_READS = {
    "issue": ("list", "ls", "view", "status"),
    "pr": ("list", "view", "diff", "status", "checks", "checkout"),
    "mr": ("list", "view", "diff", "checkout"),
    "repo": ("view", "list"),
    "release": ("list", "view"),
    "run": ("list", "view"),
    "ci": ("list", "view", "status", "get"),
    "label": ("list",),
    "milestone": ("list",),
    "auth": ("status",),
    "search": None,
    "browse": None,
}


def forge_reads_only(words, args, method):
    """True for gh/glab commands that only read: listing and viewing issues, PRs/MRs, pipelines, and API GETs."""
    if not words:
        return True
    if words[0] == "api":
        joined = " ".join(args)
        if len(words) > 1 and words[1] == "graphql":  # queries read; mutations write
            return not re.search(r"\bmutation\b", joined)
        fields = re.search(r"(^|\s)(-f|-F|--field|--raw-field|--input)\b", joined)
        return method == "GET" or (not method and not fields)
    allowed = FORGE_READS.get(words[0], ())
    return allowed is None or (len(words) > 1 and words[1] in allowed)


def forge_target_is_guest(args):
    """The repo a -R/--repo option names, if LETS set it up and its team hasn't agreed to agents."""
    target = option_value(args, ["-R", "--repo"])
    if not target:
        return None
    from . import upgrade, walkthrough

    want = re.sub(r"\.git$", "", target.rstrip("/")).split(":")[-1].split("github.com/")[-1]
    want = re.sub(r"^https?://[^/]+/", "", want).lower()
    for r in upgrade.known_repos():
        url = git_out(["remote", "get-url", "origin"], str(r)).lower()
        path = re.sub(r"\.git$", "", url.rstrip("/")).split(":")[-1]
        path = re.sub(r"^//[^/]+/", "", path)
        same = path and want and (path == want or path.endswith("/" + want) or want.endswith("/" + path))
        if same and walkthrough.is_guest(str(r)):
            return str(r)
    return None


def on_forge(prog, args, cwd):
    """gh and glab: only reading in a repo whose team hasn't agreed to agents; never merging, approving or --admin;
    opening or readying a PR/MR is shipping, which needs `lets.agents ship`."""
    from . import walkthrough

    words, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in ("-R", "--repo", "--hostname", "-H", "-X", "--method"):
            skip = True
        elif not a.startswith("-"):
            words.append(a)
    method = (option_value(args, ["-X", "--method"]) or "").upper()
    guest = forge_target_is_guest(args) or (cwd if cwd and walkthrough.is_guest(cwd) else None)
    if guest and not forge_reads_only(words, args, method):
        block(
            "The team hasn't agreed to agents working in this repo, so agents only read from its GitLab or GitHub: "
            "this %s command writes (it comments, creates, edits or closes). Tell me what to post and I'll do it "
            "myself" % prog
        )
    words, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in ("-R", "--repo", "--hostname", "-H", "-X", "--method"):
            skip = True
        elif not a.startswith("-"):
            words.append(a)
    joined = " ".join(args)
    method = (option_value(args, ["-X", "--method"]) or "").upper()
    if "--admin" in args:
        block("agents don't use --admin; it skips the team's protections")
    writes = method in ("POST", "PUT", "PATCH", "DELETE") or (
        method != "GET" and re.search(r"(^|\s)(-f|-F|--field|--raw-field|--input)\b", joined)
    )
    if words[:2] in (["pr", "merge"], ["mr", "merge"], ["mr", "accept"]) or (
        words[:1] == ["api"] and re.search(r"/(pulls|merge_requests)/\d+/merge\b", joined) and writes
    ):
        block("agents don't merge; a person merges after review")
    if (
        (words[:2] == ["pr", "review"] and re.search(r"(^|\s)(--approve|-a)\b", joined))
        or words[:2] == ["mr", "approve"]
        or (
            words[:1] == ["api"]
            and re.search(r"/(approve|approvals)\b|/reviews\b", joined)
            and method in ("POST", "PUT")
        )
    ):
        block("agents don't approve; approving is the reviewer's job")
    if prog == "gh" and words[:2] in (["pr", "create"], ["pr", "new"], ["pr", "ready"]):
        ship_allowed(cwd)
        on_ship(cwd, option_value(args, ["--base", "-B"]))
    if prog == "glab" and (
        words[:2] in (["mr", "create"], ["mr", "new"])
        or (words[:2] == ["mr", "update"] and re.search(r"(^|\s)(--ready|-r)\b|--draft=false", joined))
    ):
        ship_allowed(cwd)
        on_ship(cwd, option_value(args, ["--target-branch", "-b"]))


def ship_allowed(cwd):
    from . import walkthrough

    if walkthrough.agent_level(cwd) != "ship":
        block("agents don't open PRs here; I open it myself. `/lets:walkthrough` drafts the description")


MAKES_COMMITS = {
    "commit",
    "merge",
    "rebase",
    "cherry-pick",
    "revert",
    "am",
    "pull",
    "commit-tree",
    "update-ref",
    "filter-branch",
    "replace",
}


def branch_names(sub, args):
    """Names of branches a command creates or renames to."""
    if sub in ("checkout", "switch"):
        return [
            args[k + 1]
            for k, a in enumerate(args[:-1])
            if a in ("-b", "-B", "-c", "-C", "--orphan", "--create", "--force-create")
        ]
    if sub == "worktree" and args[:1] == ["add"]:
        return [args[k + 1] for k, a in enumerate(args[:-1]) if a in ("-b", "-B")]
    if sub == "branch":
        pos = [a for a in args if not a.startswith("-")]
        if any(a in ("-m", "-M", "--move", "-c", "-C", "--copy") for a in args):
            return pos[-1:]
        if pos and not any(
            a.startswith(
                (
                    "-d",
                    "-D",
                    "--delete",
                    "--list",
                    "-l",
                    "-a",
                    "-r",
                    "--contains",
                    "--merged",
                    "--no-merged",
                    "--points-at",
                    "--show-current",
                    "-v",
                    "--format",
                    "--sort",
                    "--set-upstream",
                    "-u",
                    "--unset-upstream",
                    "--edit-description",
                )
            )
            for a in args
        ):
            return pos[:1]
    return []


def local_git(sub, args, repo):
    """Git stays local by default, and no repo gets a trace of an AI."""
    from . import walkthrough

    if not repo:
        return
    level = walkthrough.agent_level(repo)
    if any(a in ("-h", "--help") for a in args):
        return
    aborting = any(a in ("--abort", "--quit", "--skip") for a in args)
    if (
        sub in MAKES_COMMITS
        and level == "local"
        and not aborting
        and not (sub in ("merge", "pull") and "--ff-only" in args)
    ):
        block(
            "agents don't make commits here; I commit myself. Leave the change in the working tree and tell me it's "
            "ready (`/lets:commit-message` drafts the message)"
        )
    planning = (
        git_out(["config", "--get", "lets.role"], repo) == "planning"
    )  # my private planning repo: commits on main
    if (
        sub in MAKES_COMMITS
        and level != "local"
        and not aborting
        and not (planning and sub == "commit")
        and shared_branch(current_branch(repo), repo)
    ):
        block(
            "agents commit to feature branches only; this is %s. Create a feature branch first" % current_branch(repo)
        )
    if sub == "push" and level != "ship":
        block("agents don't push here; I push myself")
    for name in branch_names(sub, args):
        if walkthrough.AI_NAME.search(name):
            block("branch names say what the work is, never who or what wrote it: rename %r" % name)


def discards(sub, args):
    """Commands that throw away uncommitted work across the tree, or an unmerged branch."""
    pos = [a for a in args if not a.startswith("-")]
    whole = lambda ps: any(p in (".", ":/", "*", ":") for p in ps)
    if sub == "reset" and any(a in ("--hard", "--merge", "--keep") for a in args):
        return True
    if sub in ("checkout", "switch") and any(a in ("-f", "--force", "--discard-changes") for a in args):
        return True
    if sub == "checkout" and "--" in args and whole(args[args.index("--") + 1 :]):
        return True
    if sub == "checkout" and whole(pos):
        return True
    if (
        sub == "restore"
        and whole(pos)
        and not (("--staged" in args or "-S" in args) and not ("--worktree" in args or "-W" in args))
    ):
        return True
    if sub == "clean" and any(re.match(r"^-[a-zA-Z]*f", a) or a == "--force" for a in args) and not pos:
        return True
    if sub == "stash" and pos[:1] in (["drop"], ["clear"]):
        return True
    if sub == "worktree" and args[:1] == ["remove"] and any(a in ("-f", "--force") for a in args):
        return True
    if sub == "branch" and ("-D" in args or ("--delete" in args and "--force" in args)):
        return True
    return False


AGENT_CONFIG = re.compile(
    r"(^|/)(CLAUDE\.md|AGENTS\.md|AGENTS\.override\.md|\.cursorrules|\.windsurfrules|"
    r"copilot-instructions\.md)$|(^|/)\.(claude|agents|codex|cursor|github/instructions)/"
)


def check_agent_config(tool, inp, cwd):
    """Where the team hasn't agreed to agents, the owners' agent config stays as they wrote it (my planning lives in my planning repo)."""
    from . import walkthrough

    for path in proposed_files(tool, inp, cwd) if tool != "NotebookEdit" else {}:
        root = git_out(
            ["rev-parse", "--show-toplevel"], os.path.dirname(path) if os.path.isdir(os.path.dirname(path)) else cwd
        )
        if not root or not walkthrough.is_guest(root):
            continue
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
        if AGENT_CONFIG.search(rel) and not rel.endswith(("settings.local.json", "CLAUDE.local.md")):
            block(
                "The team hasn't agreed to agents working in this repo, so its agent config (%s) stays as the owners wrote it. My planning "
                "and notes go in my planning repo (`lets where`)" % rel
            )


def check_edit(inp):
    paths = [str(inp.get(k, "")) for k in ("file_path", "path", "notebook_path")]
    patch = inp.get("command") or inp.get("input") or ""
    if isinstance(patch, list):
        patch = "\n".join(map(str, patch))
    # Codex apply_patch: only the file headers name paths; the body is file content.
    paths += re.findall(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", str(patch), flags=re.M)
    for p in (p.strip() for p in paths):
        if re.search(r"(^|/)\.git/", p) or re.search(r"(^|/)(\.gitconfig|\.config/git/config)$", p):
            block("edits git's own files or configuration")


def _read(path):
    try:
        with open(path) as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def _apply_hunks(text, hunks):
    """Apply Codex apply_patch hunks (lists of ' ', '-', '+' lines) to text. None when a hunk doesn't match."""
    lines, pos = text.splitlines(), 0
    for hunk in hunks:
        old = [l[1:] for l in hunk if l[:1] in (" ", "-")]
        new = [l[1:] for l in hunk if l[:1] in (" ", "+")]
        if not old:
            lines += new
            continue
        found = None
        for strip in (lambda s: s, lambda s: s.rstrip(), lambda s: s.strip()):
            for k in range(pos, len(lines) - len(old) + 1):
                if [strip(x) for x in lines[k : k + len(old)]] == [strip(x) for x in old]:
                    found = k
                    break
            if found is not None:
                break
        if found is None:
            return None
        lines[found : found + len(old)] = new
        pos = found + len(new)
    return "\n".join(lines) + "\n"


def proposed_files(tool, inp, cwd):
    """{path: (content before, content after)} for an edit, as far as the tool input tells."""
    out = {}
    if tool in ("Edit", "MultiEdit", "Write"):
        path = inp.get("file_path") or ""
        path = path if os.path.isabs(path) else os.path.join(cwd, path)
        before = _read(path)
        if tool == "Write":
            after = inp.get("content")
        else:
            after = before
            edits = inp.get("edits") if tool == "MultiEdit" else [inp]
            for e in edits or []:
                if after is None or e.get("old_string") is None or e["old_string"] not in after:
                    return {}
                after = after.replace(e["old_string"], e.get("new_string", ""), -1 if e.get("replace_all") else 1)
        if isinstance(after, str):
            out[path] = (before, after)
    elif tool == "apply_patch":
        patch = inp.get("command") or inp.get("input") or inp.get("patch") or ""
        if isinstance(patch, list):
            patch = "\n".join(map(str, patch))
        current, body, kind = None, [], None
        for line in str(patch).splitlines() + ["*** End Patch"]:
            m = re.match(r"^\*\*\* (Add File|Update File|Delete File|End Patch|Begin Patch|Move to)(?:: (.+))?$", line)
            if m and m.group(1) != "Move to":
                if current:
                    path = current if os.path.isabs(current) else os.path.join(cwd, current)
                    before = _read(path)
                    if kind == "Add File":
                        out[path] = (before, "\n".join(l[1:] for l in body if l.startswith("+")) + "\n")
                    elif kind == "Update File" and before is not None:
                        hunks, h = [], []
                        for l in body:
                            if l.startswith("@@") or l == "*** End of File":
                                if h:
                                    hunks.append(h)
                                h = []
                            elif l[:1] in (" ", "-", "+") or l == "":
                                h.append(l if l else " ")
                        if h:
                            hunks.append(h)
                        after = _apply_hunks(before, hunks)
                        if after is not None:
                            out[path] = (before, after)
                current, body, kind = m.group(2), [], m.group(1)
            elif current:
                body.append(line)
    return out


def check_edit_floor(tool, inp, cwd):
    """Refuse an edit that adds a blocking floor-guard finding. Findings are counted against the last commit, so a
    marker that was already there, or that this edit only moves within the file, isn't new; findings already in the
    working tree before this edit aren't charged to it."""
    import difflib

    from . import floor as floor_guard

    proposed = proposed_files(tool, inp, cwd)
    moved_out = {}  # per repo: lines removed elsewhere since the last commit, or by this same edit (a marker moving files)
    for path, (before, after) in proposed.items():
        where = os.path.dirname(path)
        root = git_out(["rev-parse", "--show-toplevel"], where if os.path.isdir(where) else cwd)
        if not root:
            continue
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
        if rel.startswith("..") or floor_guard.IGNORED.search(rel):
            continue
        committed = run(["git", "show", "HEAD:" + rel], root)
        base = committed.stdout if committed.returncode == 0 else None

        def found(text):
            diff = "".join(
                l if l.endswith("\n") else l + "\n"
                for l in difflib.unified_diff(
                    (base or "").splitlines(True),
                    (text or "").splitlines(True),
                    "a/" + rel if base is not None else "/dev/null",
                    "b/" + rel,
                    n=0,
                )
            )
            status = ("A" if base is None else "M") + "\t" + rel
            return floor_guard.findings(
                "diff --git a/%s b/%s\n%s" % (rel, rel, diff), status, lambda _p: text, lambda _p: base
            )

        new = [f for f in found(after) if floor_guard.blocking(f) and f not in found(before)]
        if new:
            if root not in moved_out:
                gone = set()
                for line in run(["git", "diff", "--no-color", "-U0", "HEAD"], root).stdout.splitlines():
                    if line.startswith("-") and not line.startswith("---"):
                        gone.add(floor_guard._norm(line[1:]))
                for other, (ob, oa) in proposed.items():
                    if other != path:
                        gone |= {
                            floor_guard._norm(l) for l in set((ob or "").splitlines()) - set((oa or "").splitlines())
                        }
                moved_out[root] = gone
            new = [
                f
                for f in new
                if floor_guard._norm(f[1].split(": ", 1)[-1]) not in moved_out[root]
                and not any(g.startswith(floor_guard._norm(f[1].split(": ", 1)[-1])) for g in moved_out[root])
            ]
        new = unapproved(new, root)
        if new:
            block(
                "this edit weakens a quality gate:\n"
                + explain(new, root)
                + "\nIf you are moving this test from another file, remove it there first (or move it in one patch)."
            )


def lets_entry(toks):
    """Where `lets` sits in a command's words: 0 for `lets ...`, 1 for `python3 .../lets/__main__.py ...`, else None."""
    if toks and os.path.basename(toks[0]) == "lets":
        return 0
    if len(toks) > 1 and os.path.basename(toks[0]).startswith("python"):
        rest = [t for t in toks[1:] if not t.startswith("-") or t == "-m"]
        if (
            rest[:1] == ["-m"]
            and rest[1:2] == ["lets"]
            or rest
            and re.search(r"(^|/)lets/(__main__|cli)\.py$", rest[0])
        ):
            return toks.index(rest[1] if rest[:1] == ["-m"] else rest[0])
    return None


def check_lets(toks):
    k = lets_entry(toks)
    if k is not None:
        sub = toks[k + 1] if k + 1 < len(toks) else None
        args = toks[k + 2 :]
        if sub is None or sub in LETS_AGENT_OK:
            return
        if sub == "walkthrough" and args[:1] in (["scope"], ["status"]):
            return
        if sub == "guard" and args[:1] in ([], ["log"]):
            return
        if sub == "doctor" and "--yes" not in args:
            return
        if sub == "profile" and not args:
            return
        block(
            "`lets %s` is yours to run, not an agent's: it records walkthroughs, moves files or changes setup and gates"
            % sub
        )


SHIPS = r"\b(git\b[^|;&]*\b(push|commit|commit-tree|update-ref|merge|rebase|cherry-pick|revert|am|pull|filter-branch)|gh|glab)(?![\w-])"
OPAQUE = [  # forms whose real command the guard can't read
    r"\beval\b[^;&|]*" + SHIPS,
    r"\$\((?!\s*cat\b)[^)]*" + SHIPS.replace("[^|;&]", "[^|;&)]") + r"[^)]*\)",
    r"`[^`]*" + SHIPS.replace("[^|;&]", "[^|;&`]") + r"[^`]*`",
    SHIPS + r".*\|\s*(ba|z|da|k)?sh\b",
    r"['\"][^'\"]*" + SHIPS + r"[^'\"]*['\"]\s*\|\s*(ba|z|da|k)?sh\b",
    r"\bxargs\b[^|;&]*\bgit\b",
    r"\b(python3?|node|ruby|perl)\b\s+-[ce]\b.*\b(git|gh|glab)\b.*\b(push|commit|merge|rebase|pr)\b",
    r"\bgit\b[^|;&]*\s-c\s*alias\.",
]


READ_ONLY_GIT = {"status", "log", "diff", "show", "rev-parse", "ls-files", "blame", "grep"}


def notes_folder():
    """The folder /lets:learn saves notes in, if it's your own (config.json "notes"); LETS's own folder isn't a repo."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    try:
        with open(os.path.join(base, "lets", "config.json")) as f:
            where = json.load(f).get("notes")
    except (OSError, ValueError):
        return None
    if not where or where == "off":
        return None
    return os.path.expanduser(where)


def in_notes_repo(repo):
    if not repo:  # the guard can't tell where it runs; commands that change anything are refused before this
        return False
    folder = notes_folder()
    if not folder or not os.path.isdir(folder):
        return False
    notes_top = git_out(["rev-parse", "--show-toplevel"], folder)
    here = git_out(["rev-parse", "--show-toplevel"], repo) or repo
    return bool(notes_top) and os.path.realpath(notes_top) == os.path.realpath(here)


def check_shell(cmd, cwd, depth=0, adds=None):
    if depth == 0:
        bare = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?\n.*?\n\1\b", " ", cmd, flags=re.S)
        for rx in OPAQUE:
            if re.search(rx, bare):
                unsure(
                    "it commits, pushes or opens a PR in a form the guard can't follow (eval, a command substitution, "
                    "a pipe into a shell, xargs, an alias or a script)"
                )
    where, previous, dirs = cwd, cwd, []
    adds = [] if adds is None else adds
    for seg in segments(cmd):
        toks = tokens(seg)
        plain = " ".join(toks)
        if not toks:
            continue
        if depth < 3 and os.path.basename(toks[0]) in SHELLS:
            flags = [k for k, t in enumerate(toks[1:], 1) if re.match(r"^-[a-z]*c[a-z]*$", t)]
            if flags and flags[0] + 1 < len(toks):  # bash -lc '<command>': check the inner command, as written
                check_shell(toks[flags[0] + 1], where, depth + 1, adds)
                continue
        for rx, why in BYPASS:
            if re.search(rx, seg) or re.search(rx, plain):
                block("this command %s" % why)
        if toks[0] == "cd":
            target = toks[1] if len(toks) > 1 else "~"
            where, previous = (previous, where) if target == "-" else (resolve_dir(where, target), where)
            continue
        if toks[0] == "pushd":
            dirs.append(where)
            where = resolve_dir(where, toks[1]) if len(toks) > 1 else where
            continue
        if toks[0] == "popd":
            where = dirs.pop() if dirs else None
            continue
        check_lets(toks)
        try:
            if re.search(r"\bxargs\b", seg) and RISKY.search(plain):
                raise Unchecked("its arguments come from another command")
            if re.search(r"\bxargs\b.*\bgit\b.*\b(add|rm|mv)\b", seg):
                adds.append(("unknown", [], where))
                continue
            if where is None and RISKY.search(plain):
                raise Unchecked("can't tell which repository it runs in")
            sub, args, repo = parse_git(toks, where)
            if sub and repo:
                alias = git_out(["config", "--get", "alias." + sub], repo)
                if alias.startswith("!"):
                    if RISKY.search(alias) or re.search(r"\b(push|commit)\b", alias):
                        block(
                            "this git alias runs a shell command that commits or pushes; run the real command instead"
                        )
                elif alias:
                    sub, args = alias.split()[0], alias.split()[1:] + list(args)
            if sub:
                if repo is None and RISKY.search(plain):
                    raise Unchecked("can't tell which repository it runs in")
                if (
                    sub == "config"
                    and any(a.lower() == "core.hookspath" for a in args)
                    and not any(
                        a in ("--get", "--get-all", "--get-regexp", "--list", "-l", "--show-origin") for a in args
                    )
                ):
                    block("this command changes where git hooks come from")
                if sub == "config" and gate_setting(args):
                    block("this command changes this repo's gate settings or your approvals")
                if sub == "commit" and any(
                    re.match(r"^-[a-zA-Z]*n[a-zA-Z]*$", a) and "m" not in a.split("n")[0]
                    for a in args
                    if not a.startswith("--")
                ):
                    block("this command skips git hooks (commit -n)")
                if discards(sub, args):
                    block(
                        "this command throws away uncommitted work or an unmerged branch. Ask me first; I'll run "
                        "it myself if it's right"
                    )
                if sub not in READ_ONLY_GIT and in_notes_repo(repo):
                    block(
                        "this is the git repo your learning notes are saved in. LETS never commits or changes it: "
                        "run git there yourself"
                    )
                if sub in ("add", "rm", "mv"):
                    adds.append((sub, args, repo))
                local_git(sub, args, repo)
                if sub == "push":
                    if any(a.startswith(("--delete", "-d")) for a in args) or any(a.startswith(":") for a in args):
                        targets = [a.lstrip(":") for a in args if not a.startswith("-")][1:]
                        if any(shared_branch(t, repo) for t in targets):
                            block("agents don't delete a shared branch")
                    on_git_push(args, repo)
                if sub == "commit":
                    on_commit(commit_diff_args(args), repo, adds)
                if sub in ("merge", "rebase", "cherry-pick", "revert", "am") and "--continue" in args:
                    on_commit(["--cached"], repo, adds)
            for prog in ("gh", "glab"):
                i, rest = parse_tool(toks, prog)
                if i is not None:
                    if where is None:
                        raise Unchecked("can't tell which repository it runs in")
                    on_forge(prog, rest, where)
        except SystemExit:
            raise
        except Exception as e:  # a command that commits, pushes or ships must be checked, or it doesn't run
            if isinstance(e, Unchecked):
                if RISKY.search(plain):
                    unsure(str(e))
                continue
            raise


def commit_repos(cmd, cwd):
    """The repositories the `git commit` calls in a command run in (following cd and git -C), None when unknown."""
    where, out = cwd, []
    for seg in re.split(r"&&|\|\||;|\n", cmd):
        toks = tokens(seg.strip()) if seg.strip() else []
        if not toks:
            continue
        if toks[0] == "cd":
            where = resolve_dir(where, toks[1] if len(toks) > 1 else "~")
            continue
        sub, _args, repo = parse_git(toks, where)
        if sub == "commit":
            out.append(repo)
    return out


def check_commit_message(cmd, cwd):
    """A commit message or pull request text never mentions an AI, in any repo, except the AI credit the repo chose
    (`lets where` shows it): then a commit message must end with that trailer, and with trailer-pr a pull request
    description must carry the note. Only the message is read (its -m values, a heredoc body, or the command without
    its paths)."""
    from . import walkthrough
    from .profile import PR_NOTE, ai_credit

    def credit():
        try:
            repos = commit_repos(cmd, cwd) or [cwd]
            return ai_credit(repos[0] or cwd)[:2]
        except Exception:  # noqa: BLE001  (no profile or no repo: no credit)
            return "never", ""

    if re.search(r"\b(gh\s+pr\s+(create|new|edit)|glab\s+mr\s+(create|new|update))\b", cmd):
        texts = re.findall(
            r"\s(?:--title|-t|--body|-b|--description|-d)(?:=|\s+)(\"(?:[^\"\\]|\\.)*\"|'[^']*'|\S+)", cmd
        )
        texts += [m[1] for m in re.findall(r"<<-?\s*['\"]?(\w+)['\"]?\n(.*?)\n\1\b", cmd, flags=re.S)]
        text = "\n".join(texts)
        mode, trailer = credit()
        if mode == "trailer-pr" and re.search(r"\s(--body|-b|--description|-d)\b|<<", cmd) and PR_NOTE not in text:
            block("this repo credits AI help in pull requests: end the description with the line `%s`" % PR_NOTE)
        if mode != "never":
            text = text.replace(PR_NOTE, "").replace(trailer, "")
        if walkthrough.AI_TRACE.search(text):
            block("pull request titles and descriptions say what changed, never who or what wrote it: no AI mention")
    if not (RISKY.search(cmd) and re.search(r"\bcommit\b", cmd)):
        return
    messages = re.findall(r"(?:\s-[a-zA-Z]*m|--message)(?:=|\s+)(\"(?:[^\"\\]|\\.)*\"|'[^']*'|\S+)", cmd)
    messages += [m[1] for m in re.findall(r"<<-?\s*['\"]?(\w+)['\"]?\n(.*?)\n\1\b", cmd, flags=re.S)]
    text = "\n".join(messages) if messages else " ".join(w for w in cmd.split() if "/" not in w)
    mode, trailer = credit()
    if mode != "never" and messages:
        lines = [ln.strip().strip("\"'") for ln in text.replace("\\n", "\n").splitlines()]
        if trailer not in lines:
            block(
                "this repo credits AI help in commits: end the message with the trailer `%s`, after a blank line"
                % trailer
            )
        text = "\n".join(ln for ln in lines if ln != trailer)
    if not walkthrough.AI_TRACE.search(text):
        return
    block("commit messages say what changed, never who or what wrote it: no AI mention or trailer")


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name") or ""
    inp = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    if tool in EDIT_TOOLS:
        check_edit(inp)
        check_agent_config(tool, inp, cwd)
        check_edit_floor(tool, inp, cwd)
        return
    cmd = inp.get("command")
    if isinstance(cmd, list):
        if len(cmd) >= 3 and os.path.basename(str(cmd[0])) in SHELLS and re.match(r"^-[a-z]*c[a-z]*$", str(cmd[1])):
            cmd = str(cmd[2])  # Codex sends ["bash", "-lc", "<script>"]: check the script as written
        else:
            cmd = " ".join(shlex.quote(str(c)) for c in cmd)
    if isinstance(cmd, str):
        CALL["cmd"] = cmd
        check_commit_message(cmd, cwd)
        check_shell(cmd, cwd)


def entry():
    """Run the guard. If it crashes, the crash is logged for `lets doctor`. A command that commits, pushes or ships
    still can't run unchecked (Claude Code asks me; Codex blocks it); anything else runs, since the guard's own bug
    shouldn't stop harmless work."""
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        if os.environ.get("LETS_GUARD_STRICT"):
            raise
        why = "the guard hit an internal error (%s: %s)" % (type(e).__name__, e)
        if CALL["cmd"] and not RISKY.search(CALL["cmd"]):
            log("crash", why)
            sys.exit(0)
        log("crash", why)
        unsure(why)
