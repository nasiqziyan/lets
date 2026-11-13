#!/bin/sh
# At the start of each Claude Code or Codex session: anything you need to know about LETS on this computer (the guard
# can't run, an update is out, LETS changed and needs `lets install`). Prints nothing when all is well.
here=$(dirname "$0")
if ! command -v python3 >/dev/null 2>&1; then
  echo "LETS: python3 isn't installed, so the LETS guard can't run and git, gh and glab commands will be blocked. Tell me this first: install Python 3.11 or newer, then run lets doctor."
  exit 0
fi
exec python3 -I "$here/../lib/lets/__main__.py" session-start </dev/null 2>/dev/null
