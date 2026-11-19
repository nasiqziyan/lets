# The `lets` command

`lets` sets up your computer and repos, and reports on them. The work itself happens through the commands you type in
Claude Code and Codex.

| Command | What it does |
|---|---|
| `lets install [--dry-run] [--yes] [--force] [--tools claude,codex]` | Ask the profile questions (first time), then show and make the changes that wire LETS into Claude Code and Codex. If both are installed, it asks once which to set up (`--tools` answers it). Safe to re-run. |
| `lets setup [flags]` | Set up a repo, or several related repos: where plans live, and how you build there. Re-run it to change answers or move the plans. |
| `lets profile [question]` | Change one answer in your profile. `lets profile` lists them. |
| `lets profile tools` | Change which of Claude Code and Codex LETS is set up in. A tool you drop has LETS taken out of it; you see the changes first. |
| `lets where` | Where this repo's plans are, its choices, its quick check and the additions that apply. |
| `lets sync` | Bring a team planning repo up to date (fast-forward only). |
| `lets check [--run]` | Weakened gates (skipped tests, loosened checks) in this branch's changes; `--run` then runs the quick check. |
| `lets walkthrough scope \| complete \| status` | What the walkthrough covers; `complete` records yours (only you run it). |
| `lets note [change <name> \| patch <name> \| reviewed] [--mode pair\|agent]` | What this branch is for. The building commands record it; the status line reads it. |
| `lets note base <branch \| auto>` | The branch this one merges into, for a stacked pull request: walkthroughs and checks compare against it. |
| `lets guard log [--last N]` | What the guard blocked, asked about or crashed on lately (20 by default). |
| `lets doctor [--dry-run] [--yes]` | Check the wiring, fix what can be fixed (shown first), and say what to do about the rest. |
| `lets update [--yes]` | Show what a newer LETS changes (its changelog, and the files that change how agents behave), then install it and finish setting it up. Also finishes an update made with `npm install -g` directly. |
| `lets uninstall [--dry-run] [--yes]` | Take LETS out of Claude Code and Codex. Your profile, settings and plans stay. |
| `lets statusline on \| off [--dry-run] [--yes]` | Put LETS's status line in Claude Code (the epic, the change and the task you're on), or take it out. If you have your own, it's only replaced when you agree; `off` (and `lets uninstall`) puts it back. |
| `lets statusline` | Print the status line (Claude Code passes its JSON on stdin). For your own status line script, call it and print what it prints. |
| `lets --version` | The installed version. |

## `lets setup` flags

Every question has a flag, for scripts: `--mode one|group`, `--path <repo or folder>`, `--repos a,b`,
`--planning in-repo|team|private`, `--url <planning repo clone URL>`, `--plans-dir <folder>`,
`--build pair|agent`, `--tests propose|always|ask`, `--agents local|commit|ship`, `--check '<command>'`,
`--base <branch>` (the branch work merges into; `auto` to detect it),
`--team-agreed yes|no` (has the team agreed to agents working in the repo?),
`--ai-credit never|trailer|trailer-pr|profile` (`trailer:'<line>'` for a trailer of your own), `--yes`.
`--remove` clears a repo's LETS settings (its plans stay).

## Environment

| Variable | Effect |
|---|---|
| `LETS_NO_UPDATE_CHECK=1` | No update check, whatever the profile says |
| `NO_COLOR=1` | No colour in screens or the status line |
| `XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` | Where LETS's folders go (see [settings](settings.md)) |
| `CODEX_HOME` | Codex's folder (default `~/.codex`) |
