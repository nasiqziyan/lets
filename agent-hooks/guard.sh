#!/bin/sh
# Hands each agent tool call to the LETS guard. Without python3 the guard can't run: then git, gh and glab commands
# are blocked (so nothing is committed, pushed or opened unchecked) and everything else passes.
here=$(dirname "$0")
if command -v python3 >/dev/null 2>&1; then
  exec python3 -I "$here/guard.py"
fi
if grep -Eq '(^|[^[:alnum:]_-])(git|gh|glab)([^[:alnum:]_-]|$)'; then
  echo "Blocked: the LETS guard can't run (python3 isn't installed), so git, gh and glab commands are blocked until it can. Run lets doctor." >&2
  exit 2
fi
exit 0
