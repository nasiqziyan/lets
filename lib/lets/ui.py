"""LETS's terminal screens: colour, arrow-key menus, checkboxes and text prompts (stdlib only).

Every prompt has a default. Without an interactive terminal (a script, CI, a pipe) nothing is drawn or read: each
prompt returns its default, so commands stay scriptable. Colour is off when output isn't a terminal or NO_COLOR is set.
"""

import os
import re
import shutil
import sys

try:
    import termios
    import tty
except ImportError:  # Windows without WSL: plain prompts
    termios = tty = None


def interactive():
    return sys.stdin.isatty() and sys.stdout.isatty() and termios is not None and os.environ.get("TERM") != "dumb"


def _colour_on():
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"


STYLES = {"bold": "1", "dim": "2", "cyan": "36", "green": "32", "yellow": "33", "red": "31", "magenta": "35"}


def paint(text, *styles):
    if not _colour_on() or not styles:
        return text
    return "\033[%sm%s\033[0m" % (";".join(STYLES[s] for s in styles), text)


def out(text=""):
    print(text, flush=True)


def title(text, right=""):
    """A screen's title line: the command and step on the left, progress or context on the right."""
    out()
    width = 78
    gap = max(2, width - len(text) - len(right))
    out(paint(text, "bold", "cyan") + " " * gap + paint(right, "dim"))
    out()


def note(text):
    out("  " + paint(text, "dim"))


def ok(text):
    out(paint("✓ ", "green") + text)


def warn(text):
    out(paint("! ", "yellow") + text)


def step(text):
    """The one next step a command ends with."""
    out()
    out(paint("Next: ", "bold") + text)


# ---------- reading keys ----------


def _key(fd):
    ch = os.read(fd, 1)
    if ch == b"\x1b":
        seq = os.read(fd, 2)
        return {b"[A": "up", b"[B": "down", b"[C": "right", b"[D": "left"}.get(seq, "esc")
    if ch in (b"\r", b"\n"):
        return "enter"
    if ch == b" ":
        return "space"
    if ch == b"\x03":
        raise KeyboardInterrupt
    try:
        return ch.decode()
    except UnicodeDecodeError:
        return ""


class _Raw:
    def __enter__(self):
        assert termios is not None and tty is not None  # interactive() is False without them
        self.fd = sys.stdin.fileno()
        self.saved = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        sys.stdout.write("\033[?25l")  # hide the cursor while choosing
        return self.fd

    def __exit__(self, *exc):
        assert termios is not None
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


ANSI = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


def _rows(line):
    """How many terminal rows a line takes, wrapping included."""
    cols = shutil.get_terminal_size((80, 24)).columns or 80
    return max(1, -(-len(ANSI.sub("", line)) // cols))


def _draw(lines, previous):
    if previous:
        sys.stdout.write("\033[%dA\033[J" % previous)
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
    return sum(_rows(l) for l in lines)


def _collapse(drawn, question, answer):
    """Replace a finished menu with one line, so the scrollback stays tidy."""
    sys.stdout.write("\033[%dA\033[J" % drawn)
    out(paint(question, "bold") + "  " + paint("› " + answer, "cyan"))


# ---------- prompts ----------


def select(question, options, default=None, explain=None):
    """One choice from options [(key, label, description)]. Returns the key. ↑↓ or the number, then Enter."""
    keys = [o[0] for o in options]
    pick = keys.index(default) if default in keys else 0
    if not interactive():
        return keys[pick]
    width = max(len(o[1]) for o in options) + 3

    def lines():
        ls = [paint(question, "bold")]
        if explain:
            ls += ["  " + paint(l, "dim") for l in explain.splitlines()]
        ls.append("")
        for i, (_k, label, desc) in enumerate(options):
            mark = paint("❯ ", "cyan") if i == pick else "  "
            shown = paint(label, "cyan", "bold") if i == pick else label
            ls.append("  %s%s%s %s" % (mark, shown, " " * (width - len(label)), paint(desc or "", "dim")))
        ls.append(paint("  ↑↓ move · Enter choose", "dim"))
        return ls

    drawn = _draw(lines(), 0)
    with _Raw() as fd:
        while True:
            k = _key(fd)
            if k == "up":
                pick = (pick - 1) % len(options)
            elif k == "down":
                pick = (pick + 1) % len(options)
            elif k.isdigit() and 1 <= int(k) <= len(options):
                pick = int(k) - 1
            elif k == "enter":
                break
            drawn = _draw(lines(), drawn)
    _collapse(drawn, question, options[pick][1])
    return keys[pick]


def multiselect(question, items, chosen=None, explain=None):
    """Several choices from items [(key, label)], all chosen by default. Space toggles, a toggles all, Enter confirms."""
    keys = [i[0] for i in items]
    on = set(keys if chosen is None else chosen)
    if not interactive():
        return [k for k in keys if k in on]
    pos = 0

    def lines():
        ls = [paint(question, "bold")]
        if explain:
            ls += ["  " + paint(l, "dim") for l in explain.splitlines()]
        ls.append("")
        for i, (k, label) in enumerate(items):
            box = paint("[x]", "green") if k in on else "[ ]"
            mark = paint("❯ ", "cyan") if i == pos else "  "
            ls.append("  %s%s %s" % (mark, box, paint(label, "bold") if i == pos else label))
        ls.append(paint("  ↑↓ move · space select · a all · Enter confirm", "dim"))
        return ls

    drawn = _draw(lines(), 0)
    with _Raw() as fd:
        while True:
            k = _key(fd)
            if k == "up":
                pos = (pos - 1) % len(items)
            elif k == "down":
                pos = (pos + 1) % len(items)
            elif k == "space":
                on.symmetric_difference_update({keys[pos]})
            elif k == "a":
                on = set() if len(on) == len(keys) else set(keys)
            elif k == "enter" and on:
                break
            drawn = _draw(lines(), drawn)
    picked = [k for k in keys if k in on]
    _collapse(drawn, question, ", ".join(dict(items)[k] for k in picked))
    return picked


def text(question, default=None, paths=False, explain=None, required=False):
    """A typed answer. Enter accepts the default shown in brackets. With paths=True, Tab completes folder names."""
    if not interactive():
        return default
    out(paint(question, "bold") + (paint("  [%s]" % default, "dim") if default else ""))
    if explain:
        for l in explain.splitlines():
            note(l)
    if paths:
        _path_completion()
    while True:
        try:
            arrow = paint("› ", "cyan")
            if "readline" in sys.modules and arrow != "› ":  # readline must be told which bytes don't print
                arrow = ANSI.sub(lambda m: "\001" + m.group(0) + "\002", arrow)
            got = input("  " + arrow).strip()
        finally:
            if paths:
                _no_completion()
        if got or not required or default:
            if not got and default:  # show what Enter accepted
                sys.stdout.write("\033[1A\033[2K  " + paint("› ", "cyan") + default + "\n")
                sys.stdout.flush()
            return got or default
        warn("This one needs an answer.")


def confirm(question, default=True, yes="Yes", no="No", explain=None):
    return select(question, [("y", yes, ""), ("n", no, "")], "y" if default else "n", explain) == "y"


def _path_completion():
    try:
        import glob
        import readline
    except ImportError:
        return

    def complete(prefix, state):
        full = os.path.expanduser(prefix)
        hits = [h + ("/" if os.path.isdir(h) else "") for h in glob.glob(full + "*")]
        if prefix.startswith("~"):
            home = os.path.expanduser("~")
            hits = ["~" + h[len(home) :] if h.startswith(home) else h for h in hits]
        hits.sort()
        return hits[state] if state < len(hits) else None

    readline.set_completer_delims(" \t\n")
    readline.set_completer(complete)
    readline.parse_and_bind("tab: complete")


def _no_completion():
    try:
        import readline

        readline.set_completer(None)
    except ImportError:
        pass
