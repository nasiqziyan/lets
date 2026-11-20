#!/usr/bin/env python3
"""Maintainer tools for LETS's own repo (not shipped in the package).

scripts/maint.py build                 rebuild plugin/ from plugin.map, renames.json and the sources
scripts/maint.py check                 check the sources are coherent and plugin/ is up to date
scripts/maint.py intake report|apply|add ...   review and take in upstream changes (Matt Pocock, Addy Osmani, OpenSpec)
scripts/maint.py evals [--out DIR]     assemble the eval plugin and print the commands that run the evals
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from lets.core import git, run, say  # noqa: E402
from lets.install import GUARD_ENTRY, SESSION_ENTRY  # noqa: E402

PLUGIN = ROOT / "plugin"
AGENTS_MAX_LINES = 60
SKILL_MAX_BYTES = 25000  # Claude Code keeps only the start of long skills after compaction
LISTING_WARN_CHARS = 6000  # helper descriptions loaded every session; 1% of a 200k window is about 8,000 characters


def version():
    return json.loads((ROOT / "package.json").read_text())["version"]


def frontmatter(text):
    """Parse the YAML subset skills use. Returns (dict, errors)."""
    if not text.startswith("---\n"):
        return {}, ["no frontmatter at the top of the file"]
    end = text.find("\n---", 4)
    if end < 0:
        return {}, ["frontmatter is not closed"]
    data, key, errors = {}, None, []
    for raw in text[4:end].splitlines():
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")) and key:
            data[key] = (data[key] + " " + raw.strip()).strip()
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if not m:
            errors.append("cannot parse frontmatter line: %r" % raw)
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", "|", ">-", "|-"):
            val = ""
        elif len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        elif ": " in val:
            errors.append("unquoted value for %r contains ': ' (invalid YAML; quote it)" % key)
        data[key] = val
    return data, errors


def user_invoked(fm):
    return str(fm.get("disable-model-invocation", "")).lower() in ("true", "yes", "on", "1")


def codex_user_invoked(skill_dir):
    p = skill_dir / "agents" / "openai.yaml"
    return p.exists() and re.search(r"allow_implicit_invocation:\s*false", p.read_text()) is not None


def file_map(root):
    out = {}
    for dp, _dn, fns in os.walk(str(root)):
        for fn in sorted(fns):
            p = pathlib.Path(dp) / fn
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(sorted(out.items()))


def load_lock():
    return json.loads((ROOT / "UPSTREAM.lock").read_text())


def save_lock(lock):
    (ROOT / "UPSTREAM.lock").write_text(json.dumps(lock, indent=2) + "\n")


def read_map():
    """[(name, source folder, 'user' or 'helper', note file or None)] from plugin.map."""
    out = []
    for line in (ROOT / "plugin.map").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            parts = line.split()
            out.append((parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else None))
    return out


TOP_KEYS_WE_SET = {"name", "disable-model-invocation", "user-invocable"}


def load_renames():
    data = json.loads((ROOT / "renames.json").read_text()) if (ROOT / "renames.json").exists() else {}
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _word(old):
    return re.compile(r"(?<![\w])%s(?![\w])" % re.escape(old))


def renamed(src_file, text):
    """Apply LETS's vocabulary to a vendored file. Raises when a listed phrase no longer appears (upstream reworded it)."""
    pairs = load_renames().get(src_file, [])
    for old, new in pairs:
        text, n = _word(old).subn(new, text)
        if n == 0:
            raise SystemExit(
                "renames.json: %r no longer appears in %s (upstream reworded it): update the rename table"
                % (old, src_file)
            )
    return text


def rename_survivors(src_file, text):
    """Old words still present after renaming (should be none)."""
    return [old for old, _new in load_renames().get(src_file, []) if _word(old).search(text)]


def built_skill(name, src, mode, note):
    """The SKILL.md text for one plugin entry: its source with LETS's vocabulary, name and invocation settings, the rest
    of the frontmatter and the body kept as they are, and an optional note before the body. A ref keeps its source's
    frontmatter as is (it is read, never loaded as a skill)."""
    text = renamed(src + "/SKILL.md", (ROOT / src / "SKILL.md").read_text())
    end = text.find("\n---", 4)
    head, body = text[4:end], text[end + 4 :].lstrip("\n")
    if note:
        body = (ROOT / note).read_text().rstrip() + "\n\n" + body
    if mode == "ref":
        return "---\n%s\n---\n\n%s" % (head, body)
    kept, skipping = [], False
    for line in head.splitlines():
        top = re.match(r"^([A-Za-z0-9_-]+):", line)
        if top:
            skipping = top.group(1) in TOP_KEYS_WE_SET
        if not skipping:
            kept.append(line)
    flags = ["disable-model-invocation: true"] if mode == "user" else ["user-invocable: false"]
    front = "\n".join(["name: %s" % name] + kept + flags)
    return "---\n%s\n---\n\n%s" % (front, body)


def entry_dir(name, mode):
    return "%s/%s" % ("refs" if mode == "ref" else "skills", name)


def plugin_files():
    """{path inside plugin/: bytes}: everything scripts/maint.py build writes."""
    files = {}
    v = version()
    manifest = {
        "name": "lets",
        "version": v,
        "description": "LETS: one way of working in Claude Code and Codex.",
        "author": {"name": "LETS"},
        "license": "MIT",
    }
    files[".claude-plugin/plugin.json"] = json.dumps(manifest, indent=2) + "\n"
    files[".codex-plugin/plugin.json"] = json.dumps(dict(manifest, skills="./skills/"), indent=2) + "\n"
    for name, src, mode, note in read_map():
        d = entry_dir(name, mode)
        files["%s/SKILL.md" % d] = built_skill(name, src, mode, note)
        if mode == "user":
            files["%s/agents/openai.yaml" % d] = "policy:\n  allow_implicit_invocation: false\n"
        for dp, _dn, fns in os.walk(str(ROOT / src)):
            for fn in fns:
                p = pathlib.Path(dp) / fn
                rel = str(p.relative_to(ROOT / src))
                if rel not in ("SKILL.md", "agents/openai.yaml"):
                    files["%s/%s" % (d, rel)] = p.read_bytes()
    for lic in sorted((ROOT / "vendor").glob("*/LICENSE")):  # the vendored skills' own MIT licenses ship with them
        files["LICENSES/%s.txt" % lic.parent.name] = lic.read_bytes()
    for f in sorted((ROOT / "vendor" / "addyosmani-agent-skills" / "references").glob("*.md")):
        files["refs/checklists/%s" % f.name] = f.read_bytes()
    # Claude Code runs a plugin's own hooks while the plugin is enabled: the guard comes with the commands.
    files["hooks/hooks.json"] = (
        json.dumps(
            {
                "description": "LETS guard: checks every shell command and file edit an "
                "agent makes; and a check at session start",
                "hooks": {"PreToolUse": [GUARD_ENTRY], "SessionStart": [SESSION_ENTRY]},
            },
            indent=2,
        )
        + "\n"
    )
    files["README.md"] = (
        "# Built by scripts/maint.py build from plugin.map and renames.json. Don't edit: "
        "edit the sources (skills/, vendor/, notes/) and rebuild.\n"
    )
    return {k: (v.encode() if isinstance(v, str) else v) for k, v in files.items()}


def plugin_stale():
    want = plugin_files()
    have = {}
    if PLUGIN.exists():
        for dp, _dn, fns in os.walk(str(PLUGIN)):
            for fn in fns:
                p = pathlib.Path(dp) / fn
                have[str(p.relative_to(PLUGIN))] = p.read_bytes()
    return sorted(set(want) ^ set(have) | {k for k in want if k in have and want[k] != have[k]})


def cmd_build(a=None, quiet=False):
    want = plugin_files()
    if PLUGIN.exists():
        shutil.rmtree(str(PLUGIN))
    for rel, data in want.items():
        p = PLUGIN / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    if not quiet:
        say(
            "Built plugin/: %d commands and helpers, %d references."
            % (sum(1 for e in read_map() if e[2] != "ref"), sum(1 for e in read_map() if e[2] == "ref"))
        )


RISKY = re.compile(
    r"\b(curl|wget|Invoke-WebRequest|eval|base64|chmod \+x|rm -rf|npx|pip install|bash -c)\b|\|\s*(ba)?sh\b|https?://",
    re.I,
)


def cache_dir(name):
    return pathlib.Path(os.path.expanduser("~/.cache/lets-maint/upstream")) / name


def fetch(u):
    d = cache_dir(u["name"])
    if not (d / ".git").exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--quiet", u["repo"], str(d)])
    else:
        run(["git", "fetch", "--quiet", "--tags", "origin"], cwd=d)
    run(["git", "remote", "set-head", "origin", "-a"], cwd=d, check=False)
    return d


def show(d, ref, path):
    r = run(["git", "show", "%s:%s" % (ref, path)], cwd=d, check=False)
    return r.stdout if r.returncode == 0 else None


def changelog_since(d, ref, old_version):
    text = show(d, ref, "CHANGELOG.md")
    if not text:
        return ""
    m = re.search(r"^#+\s*\[?v?%s\b" % re.escape(old_version), text, re.M)
    return (text[: m.start()] if m else text[:4000]).strip()


def skill_dirs(d, ref):
    return {
        f.rsplit("/", 1)[0]
        for f in git("ls-tree", "-r", "--name-only", ref, cwd=d).splitlines()
        if f.endswith("/SKILL.md")
    }


def cmd_intake(a):
    lock = load_lock()
    today = datetime.date.today().isoformat()
    out = ROOT / "intake"
    out.mkdir(exist_ok=True)
    if a.action == "report":
        lines = ["# Upstream intake %s" % today, ""]
        for u in lock["upstreams"]:
            lines.append("## %s" % u["name"])
            d = fetch(u)
            if u.get("mode") == "tool":
                latest = (
                    run(["npm", "view", u["npm"], "version"], check=False).stdout.strip() or "unknown (npm unreachable)"
                )
                lines.append("- pinned %s, latest %s" % (u["version"], latest))
                if latest != u["version"] and not latest.startswith("unknown"):
                    cl = changelog_since(d, "origin/HEAD", u["version"])
                    lines.append(
                        "\n<details><summary>Changelog since %s</summary>\n\n%s\n\n</details>"
                        % (u["version"], cl[:12000])
                    )
                lines.append("")
                continue
            new, old = git("rev-parse", "origin/HEAD", cwd=d), u["sha"]
            n = git("rev-list", "--count", "%s..%s" % (old, new), cwd=d, check=False) or "?"
            lines.append("- pinned %s, upstream %s (%s commits)" % (old[:12], new[:12], n))
            if new == old:
                lines.append("- nothing new\n")
                continue
            paths = u["source_paths"]
            lines.append(
                "- vendored paths that changed:\n```\n%s\n```"
                % (git("diff", "--stat", old, new, "--", *paths, cwd=d) or "none")
            )
            full = git("diff", old, new, "--", *paths, cwd=d)
            (out / today).mkdir(exist_ok=True)
            (out / today / ("%s.diff" % u["name"])).write_text(full)
            risky = sorted(
                {
                    l[1:].strip()[:120]
                    for l in full.splitlines()
                    if l.startswith("+") and not l.startswith("+++") and RISKY.search(l)
                }
            )
            if risky:
                lines.append(
                    "- added lines worth a security read:\n"
                    + "\n".join("  - `%s`" % r.replace("`", "'") for r in risky[:40])
                )
            olds, news = skill_dirs(d, old), skill_dirs(d, new)
            if news - olds:
                lines.append("- new skills upstream (not vendored): " + ", ".join(sorted(news - olds)))
            if (olds - news) & set(paths):
                lines.append(
                    "- vendored skills removed or renamed upstream: " + ", ".join(sorted((olds - news) & set(paths)))
                )
            before = after = 0
            flips = []
            for p in sorted(set(paths) & olds):
                fo, _ = frontmatter(show(d, old, p + "/SKILL.md") or "")
                fn, _ = frontmatter(show(d, new, p + "/SKILL.md") or "")
                before += 0 if user_invoked(fo) else len(fo.get("description", ""))
                after += 0 if (not fn or user_invoked(fn)) else len(fn.get("description", ""))
                if fn and user_invoked(fo) != user_invoked(fn):
                    flips.append(p)
            lines.append("- model-invoked description characters for vendored skills: %d -> %d" % (before, after))
            if flips:
                lines.append("- who may invoke it changed for: " + ", ".join(flips))
            cl = changelog_since(d, new, u["version"])
            if cl:
                lines.append(
                    "\n<details><summary>Changelog since %s</summary>\n\n%s\n\n</details>" % (u["version"], cl[:12000])
                )
            lines.append("")
        report = out / ("%s.md" % today)
        report.write_text("\n".join(lines) + "\n")
        say(str(report))
    elif a.action == "apply":
        u = next((x for x in lock["upstreams"] if x["name"] == a.name), None)
        if not u:
            raise SystemExit("unknown upstream %s" % a.name)
        if u.get("mode") == "tool":
            u["version"], u["date"] = a.ref, today
            save_lock(lock)
            say("Pinned %s to %s. Install it: npm install -g %s@%s" % (u["name"], a.ref, u["npm"], a.ref))
            return
        d = fetch(u)
        sha = git("rev-parse", a.ref, cwd=d)
        vd = ROOT / u["vendor_dir"]
        paths = a.paths or u["source_paths"]
        for p in paths:
            target = vd / p
            if target.is_dir():
                shutil.rmtree(str(target))
            elif target.exists():
                target.unlink()
            for f in git("ls-tree", "-r", "--name-only", sha, "--", p, cwd=d).splitlines():
                dst = vd / f
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(
                    subprocess.run(["git", "show", "%s:%s" % (sha, f)], cwd=str(d), stdout=subprocess.PIPE).stdout
                )
        u["files"] = file_map(vd)
        if a.paths:
            u.setdefault("path_pins", {}).update({p: sha for p in a.paths})
        else:
            u["sha"], u["date"] = sha, today
            u.pop("path_pins", None)
            manifest = show(d, sha, ".claude-plugin/plugin.json")
            if manifest:
                u["version"] = json.loads(manifest).get("version", u["version"])
        save_lock(lock)
        say(
            "Vendored %s at %s. Next: scripts/maint.py build && scripts/maint.py check, then record the decision in UPSTREAM.md."
            % (u["name"], sha[:12])
        )
    elif a.action == "add":
        if any(x["name"] == a.name for x in lock["upstreams"]):
            raise SystemExit("%s is already an upstream" % a.name)
        u = {
            "name": a.name,
            "repo": a.ref,
            "sha": "",
            "version": "",
            "date": today,
            "vendor_dir": "vendor/%s" % a.name,
            "source_paths": (a.paths or []) + ["LICENSE"],
            "mode": "verbatim",
            "files": {},
        }
        u["sha"] = git("rev-parse", "origin/HEAD", cwd=fetch(u))
        lock["upstreams"].append(u)
        save_lock(lock)
        a.ref, a.paths, a.action = u["sha"], None, "apply"
        cmd_intake(a)


def cmd_evals(a):
    """Assemble a throwaway copy of the plugin with the guard and the eval cases, for `claude plugin eval`."""
    import tempfile

    out = pathlib.Path(a.out) if a.out else pathlib.Path(tempfile.mkdtemp(prefix="lets-evals-"))
    out.mkdir(parents=True, exist_ok=True)
    for name in ("skills",):
        if not (out / name).is_symlink():
            (out / name).symlink_to(PLUGIN / name)
    for name, src in (
        ("agent-hooks", ROOT / "agent-hooks"),
        ("lib", ROOT / "lib"),
    ):
        if not (out / name).is_symlink():
            (out / name).symlink_to(src)
    # the eval runner refuses an eval directory that links outside the plugin, so the cases are copied
    shutil.rmtree(out / "evals", ignore_errors=True)
    shutil.copytree(ROOT / "evals" / "plugin", out / "evals")
    # Each case gets the shared setup (LETS installed in the run's home, a sample repo) and LETS's map, which a real
    # install loads into every session.
    lets_home = pathlib.Path(a.lets_home).resolve() if a.lets_home else ROOT
    setup = (ROOT / "evals" / "setup" / "setup.sh").read_text().replace("@LETS@", str(lets_home))
    agents_map = (ROOT / "AGENTS.md").read_text()
    for case in sorted(p for p in (out / "evals").iterdir() if (p / "prompt.md").exists()):
        extra = (case / "setup.sh").read_text() if (case / "setup.sh").exists() else ""
        (case / "setup.sh").write_text(setup + ("\n# This scenario's own setup\n" + extra if extra else ""))
        (case / "case.yaml").write_text(
            'schema_version: "1.1"\nname: %s\ncontext:\n  scaffold_script: setup.sh\nexecution:\n'
            "  append_system_prompt: %s\n" % (case.name, json.dumps(agents_map))
        )
    (out / ".claude-plugin").mkdir(exist_ok=True)
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    manifest.update(
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit",
                        "hooks": [{"type": "command", "command": 'sh "${CLAUDE_PLUGIN_ROOT}/agent-hooks/guard.sh"'}],
                    }
                ]
            },
            "experimental": {"evals": "evals"},
        }
    )
    (out / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n")
    say("Eval plugin assembled in %s" % out)
    say("Run (spends usage; pin the model you use day to day):")
    say(
        "  claude plugin eval %s --scaffold --runs 3 --model <model> --allow-tools Bash Edit Write --trust-plugin --no-publish"
        % out
    )
    say("Codex: %s/evals/codex-smoke.sh [model]" % ROOT)


def source_problems():
    """Errors and warnings in LETS's own sources: vendored files, plugin.map, skills, the map, and the built plugin."""
    errors, warnings = [], []
    for u in load_lock()["upstreams"]:
        if u.get("mode") == "verbatim":
            actual, locked = file_map(ROOT / u["vendor_dir"]), u["files"]
            if actual != locked:
                diff = sorted(set(actual) ^ set(locked) | {k for k in actual if k in locked and actual[k] != locked[k]})
                errors.append(
                    "%s: vendored files differ from UPSTREAM.lock (no hand edits; use intake): %s"
                    % (u["name"], ", ".join(diff[:8]))
                )
    names, model, listing, texts, seen = {}, set(), 0, {}, set()
    for name, src, mode, note in read_map():
        d = ROOT / src
        if mode not in ("user", "helper", "ref"):
            errors.append("plugin.map: %s: who invokes it must be user, helper or ref, not %r" % (name, mode))
        if not (d / "SKILL.md").exists():
            errors.append("plugin.map: %s: no SKILL.md in %s" % (name, src))
            continue
        if note and not (ROOT / note).exists():
            errors.append("plugin.map: %s: note %s doesn't exist" % (name, note))
        text = (d / "SKILL.md").read_text()
        fm, errs = frontmatter(text)
        errors += ["%s: %s" % (src, e) for e in errs]
        if not fm.get("description") or len(fm["description"]) > 1024:
            errors.append("%s: description missing or over 1,024 characters" % src)
        key = (name, mode == "ref")
        if key in seen:
            errors.append("plugin.map: duplicate name %s" % name)
        seen.add(key)
        try:
            survivors = rename_survivors(src + "/SKILL.md", renamed(src + "/SKILL.md", text))
        except SystemExit as e:
            errors.append(str(e))
            survivors = []
        if survivors:
            errors.append("%s: old words survive the rename table: %s" % (src, ", ".join(survivors)))
        if mode == "ref":
            continue
        names[name] = src
        if src.startswith("skills/") and fm.get("name") != name:
            errors.append("%s: its name %r doesn't match plugin.map's %r" % (src, fm.get("name"), name))
        size = len(built_skill(name, src, mode, note).encode())
        if size > SKILL_MAX_BYTES:
            errors.append(
                "%s: SKILL.md is %d bytes, over %d; it would be cut after compaction" % (name, size, SKILL_MAX_BYTES)
            )
        if mode == "helper":
            model.add(name)
            listing += len(name) + len(fm.get("description", "")) + 4
        texts[name] = text
    refs = {n for n, _s, m, _n in read_map() if m == "ref"}
    for name, text in texts.items():
        for pair in re.findall(
            r"[Cc]alls? the Skill tool (?:twice, )?(?:with|for) [`\"]([\w-]+)[`\"](?:\s+and\s+[`\"]([\w-]+)[`\"])?",
            text,
        ):
            for t in filter(None, pair):
                if t not in names:
                    errors.append("%s calls %r, which is not in the plugin" % (name, t))
                elif t not in model:
                    errors.append("%s calls %r, which is user-invoked and cannot be called by a skill" % (name, t))
    shipped = ROOT / "plugin"
    for name in [n for n, s in names.items() if s.startswith("skills/")]:
        extra = "".join(p.read_text() for p in (ROOT / names[name]).glob("*.md") if p.name != "SKILL.md")
        for path in re.findall(r"~/lets/([\w./-]*[\w/])", texts[name] + extra):
            if not (ROOT / path.rstrip("/")).exists() and not (shipped / path.rstrip("/")).exists():
                errors.append("%s mentions ~/lets/%s, which does not exist" % (name, path))
        for verb in re.findall(r"/lets:([\w-]+)", texts[name] + extra):
            if verb not in names:
                errors.append("%s mentions /lets:%s, which isn't a LETS command" % (name, verb))
    for f in ["AGENTS.md", "README.md", "guides/planning.md"] + [
        str(p.relative_to(ROOT)) for p in (ROOT / "docs").rglob("*.md")
    ]:
        for verb in re.findall(r"/lets:([\w-]+)", (ROOT / f).read_text()):
            if verb not in names:
                errors.append("%s mentions /lets:%s, which isn't a LETS command" % (f, verb))
    for g in re.findall(r'Skill tool with \\?"([\w-]+)', (ROOT / "openspec" / "config.yaml").read_text()):
        if g not in model:
            errors.append("openspec/config.yaml points the agent at %r, which is not a helper skill" % g)
    if listing > LISTING_WARN_CHARS:
        warnings.append("helper descriptions total %d characters (warn above %d)" % (listing, LISTING_WARN_CHARS))
    agents = [line for line in (ROOT / "AGENTS.md").read_text().splitlines() if not line.startswith("<!--")]
    if len(agents) > AGENTS_MAX_LINES:
        errors.append(
            "AGENTS.md has %d lines; keep it under %d (a map, not a manual)" % (len(agents), AGENTS_MAX_LINES)
        )
    for path in re.findall(r"~/lets/([\w./-]*[\w/])", (ROOT / "AGENTS.md").read_text()):
        if not (ROOT / path.rstrip("/")).exists():
            errors.append("AGENTS.md mentions ~/lets/%s, which does not exist" % path)
    stale = plugin_stale()
    if stale:
        errors.append(
            "plugin/ is out of date with plugin.map and its sources (%s): run scripts/maint.py build"
            % ", ".join(stale[:5])
        )
    return errors, warnings, (names, model, listing, refs)


def cmd_check(a=None):
    errors, warnings, (names, model, listing, refs) = source_problems()
    say(
        "Skills: %d (%d you type, %d helpers; helper descriptions %d characters); %d references."
        % (len(names), len(names) - len(model), len(model), listing, len(refs))
    )
    for w in warnings:
        say("  warning: " + w)
    for e in errors:
        say("  ERROR: " + e)
    if errors:
        raise SystemExit(1)
    say("Sources: all checks pass.")


def main():
    p = argparse.ArgumentParser(prog="scripts/maint.py", description=(__doc__ or "").splitlines()[0])
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("build").set_defaults(fn=cmd_build)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    s = sub.add_parser("evals")
    s.add_argument("--lets-home", help="the LETS copy the scenarios install from (default: this repo)")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_evals)
    s = sub.add_parser("intake")
    s.add_argument("action", choices=["report", "apply", "add"])
    s.add_argument("name", nargs="?")
    s.add_argument("ref", nargs="?")
    s.add_argument("--paths", nargs="*")
    s.set_defaults(fn=cmd_intake)
    a = p.parse_args()
    if not getattr(a, "fn", None):
        p.print_help()
        raise SystemExit(2)
    a.fn(a)


if __name__ == "__main__":
    main()
