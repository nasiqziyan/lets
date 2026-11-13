# Troubleshooting

Start with `lets doctor`: it checks the wiring, fixes what it can (after showing you), and points here for the rest.

## Python

LETS needs Python 3.11 or newer. Without it, `lets` says so, and the guard blocks `git`, `gh` and `glab` for agents.

- Ubuntu or Debian: `sudo apt install python3` (on older releases, a newer `python3.12` package, or the deadsnakes PPA)
- macOS: `brew install python`

## Claude Code

`lets doctor` says Claude Code doesn't list `lets@skills-dir`: update Claude Code, then `lets install`. Run
`/reload-plugins`, or start a new session, after installing or updating LETS.

## Codex

- Codex asks before running a new hook: open Codex and trust LETS's hooks with `/hooks`. Until then, the guard isn't
  running in Codex.
- `lets doctor` says Codex's copy of the plugin is out of date: `codex plugin add lets@lets`, or `lets install`.

## `lets` runs a different program

Another tool (a task runner) is also called `lets`. `lets install` warns when it comes first on your PATH. Use
`~/lets/bin/lets`, or put `~/.local/bin` (or npm's bin folder) earlier in your PATH.

## The guard

- A block you think is wrong: the message says why, and for a weakened gate prints the command that approves it on
  this branch. If the guard is plainly wrong, report it with the command it blocked.
- The guard hit an internal error: the call is blocked and the error shown. Run `lets doctor`; if it happens again,
  report it with the details from `~/.local/state/lets/logs/`.

## An unexpected error

`lets` writes the details to `~/.local/state/lets/logs/<date>.log` and says what it had already changed. Re-running
the same command carries on from there. Please report it, with that file.
