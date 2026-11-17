"""Every place LETS reads or writes.

Paths are worked out from the environment each time they're asked for, so the tests can point LETS at a throwaway
home (LETS_TEST_HOME, XDG_*_HOME, CODEX_HOME). Settings that travel between computers live in the config folder;
backups and logs belong to this computer and live in the state folder (the XDG Base Directory layout).
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil

Path = pathlib.Path

ROOT = Path(__file__).resolve().parents[2]  # the installed package: lib/lets/paths.py -> package root
PLUGIN = ROOT / "plugin"  # built by scripts/maint.py from plugin.map; shipped built
BEGIN, END = "<!-- lets:begin -->", "<!-- lets:end -->"
MARKETPLACE = "lets"  # Codex installs the plugin as lets@lets
PACKAGE = "@nasiq/lets"
ISSUES = "https://github.com/nasiqziyan/lets/issues"


def _xdg(var: str, default: str) -> Path:
    base = os.environ.get(var)
    return Path(base) if base else P.home / default


class Paths:
    """Every place LETS touches outside its own package."""

    @property
    def home(self) -> Path:
        return Path(os.environ.get("LETS_TEST_HOME") or os.path.expanduser("~"))

    @property
    def link(self) -> Path:
        """~/lets: the stable path every installed file points through."""
        return self.home / "lets"

    # Claude Code
    @property
    def claude(self) -> Path:
        return self.home / ".claude"

    @property
    def claude_md(self) -> Path:
        return self.claude / "CLAUDE.md"

    @property
    def claude_settings(self) -> Path:
        return self.claude / "settings.json"

    @property
    def claude_plugin(self) -> Path:
        return self.claude / "skills" / "lets"

    # Codex
    @property
    def codex(self) -> Path:
        return Path(os.environ.get("CODEX_HOME") or str(self.home / ".codex"))

    @property
    def codex_agents(self) -> Path:
        return self.codex / "AGENTS.md"

    @property
    def codex_hooks(self) -> Path:
        return self.codex / "hooks.json"

    @property
    def codex_config(self) -> Path:
        return self.codex / "config.toml"

    # LETS's own folders
    @property
    def config(self) -> Path:
        """Settings that travel: profile.md, config.json, additions/."""
        return _xdg("XDG_CONFIG_HOME", ".config") / "lets"

    @property
    def profile(self) -> Path:
        return self.config / "profile.md"

    @property
    def settings(self) -> Path:
        return self.config / "config.json"

    @property
    def additions(self) -> Path:
        return self.config / "additions"

    @property
    def state(self) -> Path:
        """This computer only: backups and logs."""
        return _xdg("XDG_STATE_HOME", ".local/state") / "lets"

    @property
    def backups(self) -> Path:
        return self.state / "backups"

    @property
    def logs(self) -> Path:
        return self.state / "logs"

    @property
    def learning(self) -> Path:
        """Notes /lets:learn writes: yours, kept outside the package so updates never touch them."""
        return _xdg("XDG_DATA_HOME", ".local/share") / "lets" / "learning"

    @property
    def cache(self) -> Path:
        return _xdg("XDG_CACHE_HOME", ".cache") / "lets"

    @property
    def local_bin(self) -> Path:
        return self.home / ".local" / "bin"


P = Paths()


def short_path(p: os.PathLike | str) -> str:
    """A path as people type it: ~/... under the home folder."""
    s = str(p)
    for home in dict.fromkeys((str(P.home), os.path.realpath(P.home))):  # HOME may be a link (/var -> /private/var)
        if s == home or s.startswith(home + os.sep):
            return "~" + s[len(home) :]
    return s


def tilde(p: os.PathLike | str) -> str:
    """The form LETS stores: ~-relative, so settings carried to another computer still point at the right place."""
    return short_path(p)


def expand(p: str) -> Path:
    return Path(os.path.expanduser(p.replace("~", str(P.home), 1) if p.startswith("~") else p))


def codex_cli() -> str | None:
    return shutil.which("codex")


def has_claude() -> bool:
    return bool(shutil.which("claude")) or P.claude.exists()


def has_codex() -> bool:
    return bool(codex_cli()) or P.codex.exists()


def chosen_tools() -> list[str] | None:
    """The tools you chose for LETS (`lets install` asks when it finds both; `lets profile tools`), or None: every
    tool it finds."""
    try:
        tools = json.loads(P.settings.read_text()).get("tools")
    except (OSError, ValueError):
        return None
    return tools if isinstance(tools, list) else None


def uses_claude() -> bool:
    """Claude Code is installed and LETS is set up in it (unless you chose otherwise)."""
    tools = chosen_tools()
    return has_claude() and (tools is None or "claude" in tools)


def uses_codex() -> bool:
    tools = chosen_tools()
    return has_codex() and (tools is None or "codex" in tools)


def codex_plugin_root() -> Path | None:
    """Where Codex keeps its installed copy of the plugin (it copies; it doesn't link)."""
    cache = P.codex / "plugins" / "cache" / MARKETPLACE / "lets"
    versions = sorted(cache.iterdir(), key=lambda p: p.stat().st_mtime) if cache.exists() else []
    return versions[-1] if versions else None


def version() -> str:
    import json

    return json.loads((ROOT / "package.json").read_text())["version"]
