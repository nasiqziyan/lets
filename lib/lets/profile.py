"""Your profile: how you like to work. Asked at install, changed any time with `lets profile`, loaded into every
session of Claude Code and Codex with LETS's map."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from . import settings, ui
from .core import LetsError
from .paths import ROOT, P, expand, short_path, tilde


@dataclass(frozen=True)
class Option:
    key: str
    label: str
    hint: str
    text: str | None  # what the profile says when this is chosen; None for "type your own"


@dataclass(frozen=True)
class Choice:
    key: str
    heading: str
    question: str
    explain: str | None
    options: list[Option]
    default: str
    repo: bool = False  # each repo can choose differently at setup (stored in git config)

    def option(self, key: str) -> Option:
        return next(o for o in self.options if o.key == key)


def _len(words: str) -> str:
    return (
        "about %s words\n- Pace explanations and lessons at about %s words per message: stop at a natural break, "
        "pause for my questions, and carry on in the next message. Split, don't squeeze: never shorten an "
        "explanation to fit, and keep every definition, example and step." % (words, words)
    )


CHOICES: list[Choice] = [
    Choice(
        "build",
        "How we build (the default for each repo)",
        "How do you want to build by default?",
        "Each repo can choose differently when you set it up. Any build can override it: --pair or --agent.",
        [
            Option(
                "pair",
                "Pair",
                "you write the code; the agent explains what and why, then checks it (recommended)",
                "pair\n- Pair: give me the wider context, tell me what code to write and why it works, let me write it, "
                "then check it.\n- When I hand you a piece, write that piece only. Agent mode only when I say so.",
            ),
            Option(
                "agent",
                "Agent",
                "the agent writes the code, then walks you through it",
                "agent\n- You write the code, then walk me through it before we call it done. Pair only when I say so.",
            ),
        ],
        "pair",
        repo=True,
    ),
    Choice(
        "tests",
        "Test-first (the default for each repo)",
        "Test-first: write a failing test before the code that makes it pass?",
        "The agent always writes the tests itself. Each repo can choose differently when you set it up.",
        [
            Option(
                "propose",
                "Propose per task",
                "the agent suggests yes or no for each task, and asks (recommended)",
                "propose per task and wait\n- For each task, propose test-first or not with one line of why, and wait "
                "for me to confirm.",
            ),
            Option(
                "always",
                "Always",
                "every task starts with a failing test",
                "always\n- Every task is built test-first, starting with a failing test.",
            ),
            Option(
                "ask",
                "Only when I ask",
                "build first; tests are still added",
                "only when I ask\n- Build without test-first unless I ask for it; still add tests for what you build.",
            ),
        ],
        "propose",
        repo=True,
    ),
    Choice(
        "git",
        "How far agents may go with git (the default for each repo)",
        "How far may agents go with git by default?",
        "Agents never merge, approve, or push to a shared branch, whatever you choose. Each repo can choose differently.",
        [
            Option(
                "local",
                "Local",
                "agents branch and stash; you commit and push (recommended)",
                "local\n- Agents may create, switch and stash local branches. I commit and push.",
            ),
            Option(
                "commit",
                "Commit",
                "agents may also commit to feature branches; you push",
                "commit\n- Agents may also commit to a feature branch. I push.",
            ),
            Option(
                "ship",
                "Ship",
                "agents may also push feature branches and open pull requests; you merge",
                "ship\n- Agents may also push a feature branch and open the pull request. I merge.",
            ),
        ],
        "local",
        repo=True,
    ),
    Choice(
        "ai-credit",
        "AI credit in commits and pull requests (the default for each repo)",
        "Should commits say an AI helped write them?",
        "Branch names never mention an AI, whatever you choose. A repo can choose differently: `lets setup --ai-credit`.",
        [
            Option(
                "never",
                "No",
                "commit messages and pull requests never mention an AI (recommended)",
                "never\n- Commit messages and pull request text never mention an AI, and carry no AI trailer.",
            ),
            Option("trailer", "A trailer in each commit", "a last line such as `Assisted-by: Claude Code`", None),
            Option(
                "trailer-pr",
                "A trailer, and a note in each pull request",
                "the trailer, and the line `%s` at the end of each pull request description"
                % "Made with AI assistance.",
                None,
            ),
        ],
        "never",
        repo=True,
    ),
    Choice(
        "questions",
        "How to ask me questions when planning",
        "How should the agent ask you questions when planning?",
        None,
        [
            Option(
                "one",
                "One decision at a time",
                "each question waits for your answer (recommended)",
                "one decision at a time\n- Ask one decision at a time, with your recommended answer, and wait for my "
                "answer before the next.",
            ),
            Option(
                "rounds",
                "In rounds",
                "a numbered batch of the questions that are ready, each with a recommended answer",
                "in rounds\n- Ask in rounds: the questions that can be answered now, numbered, each with your "
                "recommended answer. 'yes' accepts every recommendation; I answer the rest by number.",
            ),
        ],
        "one",
    ),
    Choice(
        "suggestions",
        "Suggestions the agent may make",
        "May the agent suggest learning detours and retros?",
        None,
        [
            Option(
                "on",
                "Yes",
                "a learning detour when a concept is new to you, a retro after a change (recommended)",
                "all on\n- When a concept is new to me, suggest a detour: `/branch` (Claude Code) or `/fork` (Codex), "
                "then `/lets:learn`.\n- Suggest `/lets:retro` after a change is closed, or when the same mistake "
                "happens twice.",
            ),
            Option("off", "No", "you'll ask when you want one", "off\n- Don't suggest detours or retros; I'll ask."),
        ],
        "on",
    ),
    Choice(
        "notes",
        "Learning notes",
        "Where should `/lets:learn` save your notes?",
        "It asks before saving one. A note is plain Markdown, one per concept, so any notes app can read it.",
        [
            Option(
                "lets",
                "In LETS's folder",
                "%s (recommended)" % short_path(P.learning),
                "LETS's folder\n- `/lets:learn` saves notes in `%s`." % short_path(P.learning),
            ),
            Option("custom", "In a folder of yours", "type its path, such as a notes app's folder", None),
            Option(
                "off",
                "Don't save notes",
                "`/lets:learn` won't offer one",
                "none\n- Don't offer notes after `/lets:learn`.",
            ),
        ],
        "lets",
    ),
    Choice(
        "length",
        "Message length",
        "How long should explanations and lessons be, per message?",
        "Long explanations are split across messages, never shortened to fit.",
        [
            Option("short", "Short", "about 250 words, then a pause for questions", _len("250")),
            Option("medium", "Medium", "about 500 words, then a pause for questions (recommended)", _len("500")),
            Option(
                "natural",
                "As long as the explanation needs",
                "no fixed length; a pause for questions at its end",
                "as long as the explanation needs\n- No fixed length: stop at the explanation's natural end, then "
                "pause for my questions.",
            ),
            Option("custom", "Your own number", "type a word count; a pause for questions after each message", None),
        ],
        "medium",
    ),
    Choice(
        "updates",
        "Update notices",
        "Tell you when a new version of LETS is out?",
        "LETS asks the npm registry for its latest version number, at most once a day. Nothing about you is sent.",
        [
            Option(
                "on",
                "Yes",
                "a one-line notice in lets commands and at session start (recommended)",
                "on\n- (LETS's own setting: it checks for a new version at most once a day.)",
            ),
            Option(
                "off",
                "No",
                "run `lets update` when you want to check",
                "off\n- (LETS's own setting: no update checks.)",
            ),
        ],
        "on",
    ),
]
TEXTS: list[tuple[str, str]] = [
    ("explaining", "How to explain things to me (planning, grilling, reviews)"),
    ("teaching", "How to teach me a concept (`/lets:learn`)"),
    ("code-style", "Code style (where the repo has no standard of its own)"),
]
KEYS = [c.key for c in CHOICES] + [k for k, _ in TEXTS]


def choice(key: str) -> Choice:
    return next(c for c in CHOICES if c.key == key)


PR_NOTE = "Made with AI assistance."
TRAILERS = ["Assisted-by: Claude Code", "Co-authored-by: Claude <noreply@anthropic.com>", "Generated-by: Claude Code"]


def credit_text(mode: str, trailer: str = "") -> str:
    """The profile's text for an AI-credit answer; mode is never, trailer or trailer-pr."""
    if mode == "never":
        return choice("ai-credit").option("never").text or ""
    if mode == "trailer":
        return "trailer: %s\n- End each commit message with the trailer `%s`, after a blank line." % (trailer, trailer)
    return (
        "trailer and PR note: %s\n- End each commit message with the trailer `%s`, after a blank line, and each pull "
        "request description with the line `%s`." % (trailer, trailer, PR_NOTE)
    )


def parse_credit(value: str) -> tuple[str, str]:
    """(mode, trailer) from a profile answer's first line or a repo's `lets.ai-credit` (never, trailer:<line> or
    trailer-pr:<line>)."""
    value = value.strip()
    for prefix, mode in (
        ("trailer and PR note:", "trailer-pr"),
        ("trailer-pr:", "trailer-pr"),
        ("trailer:", "trailer"),
    ):
        if value.startswith(prefix):
            return mode, value[len(prefix) :].strip() or TRAILERS[0]
    return "never", ""


def ai_credit(root=None) -> tuple[str, str, bool]:
    """(mode, trailer, set for this repo) for a repo: its `lets.ai-credit`, else your profile's answer."""
    if root is not None:
        r = subprocess.run(["git", "-C", str(root), "config", "lets.ai-credit"], text=True, capture_output=True)
        if r.returncode == 0 and r.stdout.strip():
            mode, trailer = parse_credit(r.stdout)
            return mode, trailer, True
    first = current().get(choice("ai-credit").heading, "").split("\n", 1)[0].replace("Answer:", "")
    mode, trailer = parse_credit(first)
    return mode, trailer, False


def ask_trailer(default: str) -> str:
    options = [(t, t, "") for t in TRAILERS] + [("custom", "Your own", "type the line")]
    got = ui.select("Which trailer?", options, default if default in TRAILERS else TRAILERS[0])
    while got == "custom":
        typed = str(ui.text("The trailer line?", default) or "").strip()
        if re.match(r"^[A-Za-z][\w-]*: \S", typed):
            return typed
        ui.warn("A trailer looks like `Name: value`, such as `Assisted-by: Claude Code`.")
    return got


def notes_text(folder: str) -> str:
    return "a folder of mine\n- `/lets:learn` saves notes in `%s`." % folder


def choice_text(key: str, answer: str, custom: int | str | None = None) -> str:
    if answer == "custom":
        return notes_text(str(custom)) if key == "notes" else _len(str(custom))
    return choice(key).option(answer).text or ""


def sections(text: str) -> dict[str, str]:
    """{heading: body} for each '## N. Heading' section of a profile."""
    out: dict[str, list[str]] = {}
    cur = None
    for line in text.splitlines():
        m = re.match(r"^## \d+\. (.+)$", line)
        if m:
            cur = m.group(1).strip()
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {h: "\n".join(b).strip() for h, b in out.items()}


def current() -> dict[str, str]:
    return sections(P.profile.read_text()) if P.profile.exists() else {}


def write(answers: dict[str, object], keep: dict[str, str] | None = None) -> None:
    """Write the profile. answers: {key: text, or True/False for the text sections}; keep: sections carried over."""
    keep = keep or {}
    lines = [
        "# My LETS profile",
        "",
        "How I like to work. LETS loads this with its map in every session of Claude Code and Codex. Change an "
        "answer with `lets profile`, or edit this file and run `lets profile` once so Codex gets the new copy.",
        "",
    ]
    n = 0
    for c in CHOICES:
        n += 1
        body = keep.get(c.heading) or "Answer: " + str(answers.get(c.key) or choice_text(c.key, c.default))
        first, _, rest = body.partition("\n")
        lines += ["## %d. %s" % (n, c.heading), first] + ([rest] if rest else []) + [""]
    for key, heading in TEXTS:
        n += 1
        if heading in keep and key not in answers:
            body = keep[heading]
        elif answers.get(key, True):
            body = "Answer:\n" + (ROOT / "profile" / ("%s.md" % key)).read_text().rstrip()
        else:
            body = "Answer:\n- (Write your own, or delete this section.)"
        lines += ["## %d. %s" % (n, heading), body, ""]
    P.profile.parent.mkdir(parents=True, exist_ok=True)
    P.profile.write_text("\n".join(lines))


def answer(key: str) -> str:
    """The option chosen for one profile choice (or its default)."""
    c = choice(key)
    first = current().get(c.heading, "").split("\n", 1)[0].replace("Answer:", "").strip()
    for o in c.options:
        if o.text and o.text.split("\n", 1)[0] == first:
            return o.key
    if key == "length" and re.match(r"about \d+ words$", first):
        return "custom"
    if key == "notes" and first == "a folder of mine":
        return "custom"
    if key == "ai-credit":
        return parse_credit(first)[0]
    return c.default


def ask(c: Choice) -> str:
    """Ask one choice; returns the profile text for the answer."""
    got = ui.select(
        c.question,
        [(o.key, o.label, o.hint) for o in c.options],
        answer(c.key) if P.profile.exists() else c.default,
        c.explain,
    )
    if c.key == "notes":
        return ask_notes(got)
    if c.key == "ai-credit":
        return credit_text(got, ask_trailer(ai_credit()[1]) if got != "never" else "")
    if got == "custom":
        while True:
            n = str(ui.text("Words per message?", "500") or "")
            if n.isdigit() and int(n) > 0:
                return choice_text(c.key, "custom", int(n))
            ui.warn("Type a number of words, such as 400.")
    return choice_text(c.key, got)


def ask_notes(got: str) -> str:
    """The notes answer: also recorded in config.json, where the guard and the folder permissions read it."""
    if got != "custom":
        settings.set_notes_dir("off" if got == "off" else None)
        return choice_text("notes", got)
    while True:
        typed = str(ui.text("Which folder?", None, paths=True) or "").strip()
        if not typed:
            ui.warn("Type a folder's path, such as ~/notes/learning.")
            continue
        folder = expand(typed)
        if not folder.is_absolute():
            ui.warn("Type the full path (it can start with ~).")
            continue
        break
    top = subprocess.run(
        ["git", "-C", str(folder if folder.exists() else folder.parent), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
    )
    if top.returncode == 0:
        ui.note(
            "That folder is in a git repo. LETS never commits your notes: the guard stops agents running git there."
        )
        remotes = subprocess.run(["git", "-C", top.stdout.strip(), "remote", "-v"], text=True, capture_output=True)
        if remotes.stdout.strip():
            ui.warn(
                "That repo has a remote (%s). Anything you push from it leaves this computer, so notes made in repos "
                "whose team hasn't agreed to agents leave out the repo's name and use made-up examples."
                % ": ".join(remotes.stdout.split()[:2])
            )
    settings.set_notes_dir(str(folder))
    return notes_text(tilde(folder))


def ensure(dry: bool) -> str | None:
    """Ask the questions an existing profile doesn't answer yet (all of them the first time). Returns a summary."""
    have = current()
    missing = [c for c in CHOICES if c.heading not in have]
    texts = [(k, h) for k, h in TEXTS if h not in have]
    total = len(missing) + len(texts)
    if not total:
        return None
    if dry:
        return "would ask %d profile question(s) and write %s" % (total, short_path(P.profile))
    answers: dict[str, object] = {}
    for i, c in enumerate(missing, 1):
        _step(i, total)
        answers[c.key] = ask(c)
    for j, (key, heading) in enumerate(texts, len(missing) + 1):
        _step(j, total)
        answers[key] = ui.confirm(
            "Use LETS's default for '%s'?" % heading,
            True,
            "Yes",
            "No, I'll write my own",
            "You can read and edit it afterwards in %s" % short_path(P.profile),
        )
    write(answers, have)
    return "your profile: %s" % short_path(P.profile)


def _step(number: int, total: int) -> None:
    if number == 1:
        ui.title("LETS install", "your profile · %d question%s" % (total, "" if total == 1 else "s"))
        ui.note(
            "How you like to work. Each has a default: press Enter to keep it. `lets profile` changes any answer later."
        )
        ui.out()
    elif ui.interactive():
        ui.out()


def resolve(word: str) -> str:
    """A profile question from its name or a prefix of it (`len` -> length)."""
    hits = [k for k in KEYS if k == word] or [k for k in KEYS if k.startswith(word)]
    if len(hits) != 1:
        raise LetsError("No single profile question matches %r. The questions: %s." % (word, ", ".join(KEYS)))
    return hits[0]


def summary_line(key: str) -> str:
    if key in [k for k, _ in TEXTS]:
        body = current().get(dict(TEXTS)[key], "")
        default = (ROOT / "profile" / ("%s.md" % key)).read_text().rstrip()
        return "LETS's default" if body == "Answer:\n" + default else "your own"
    c = choice(key)
    got = answer(key)
    if key == "ai-credit" and got != "never":
        mode, trailer, _ = ai_credit()
        return "%s `%s`" % (c.option(mode).label, trailer)
    if got == "custom" and key == "notes":
        return short_path(settings.notes_dir() or "")
    if got == "custom":
        return current().get(c.heading, "").split("\n", 1)[0].replace("Answer:", "").strip()
    return c.option(got).label


def cmd_profile(a) -> None:
    """`lets profile`: list the answers and re-ask the one you pick; `lets profile <question>` goes straight to it."""
    if not P.profile.exists():
        raise LetsError("You have no profile yet: `lets install` asks its questions.")
    if a.question and len(a.question) >= 2 and "tools".startswith(a.question.lower()):
        from .install import cmd_tools

        cmd_tools()
        return
    key = resolve(a.question) if a.question else None
    if key is None:
        if not ui.interactive():
            for k in KEYS:
                ui.out("%-12s %s" % (k, summary_line(k)))
            ui.note("Change one with `lets profile <question>` in a terminal.")
            return
        ui.title("LETS profile", short_path(P.profile))
        key = ui.select("Which answer do you want to change?", [(k, k, summary_line(k)) for k in KEYS], KEYS[0])
    have = current()
    if key in [k for k, _ in TEXTS]:
        heading = dict(TEXTS)[key]
        use_default = ui.confirm(
            "Use LETS's default for '%s'?" % heading,
            summary_line(key) == "LETS's default",
            "Yes, LETS's default",
            "No, keep mine",
            "Yours is in %s, under '%s'." % (short_path(P.profile), heading),
        )
        if not use_default:
            ui.ok("Kept yours. Edit it in %s." % short_path(P.profile))
            return
        have.pop(heading, None)
        write({key: True}, have)
    else:
        c = choice(key)
        if not ui.interactive():
            raise LetsError("`lets profile %s` asks a question: run it in a terminal." % key)
        old_notes = settings.notes_dir()
        text = ask(c)
        have.pop(c.heading, None)
        write({key: text}, have)
        if key == "notes":
            from .install import after_notes_moved

            after_notes_moved(old_notes, settings.notes_dir())
        if c.repo:
            ui.note("This is the default for new repos. A repo's own choice is changed by running `lets setup` in it.")
    from .install import refresh_codex_copy

    refresh_codex_copy()
    ui.ok("Saved: %s is now %s." % (key, summary_line(key)))
