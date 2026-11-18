# Changelog

LETS follows [semantic versioning](https://semver.org). Each release lists what changes for you, and anything you
need to do.

## 1.1.0

### What you need to do

- Update: `npm install -g @nasiq/lets`, then `lets install`. Install lists any repo set up by an older LETS.
- In each repo it lists, run `lets setup`. It asks only the new question below and keeps every other answer.
- Codex: open Codex once, type `/hooks` and trust LETS's hooks again.

### Changes

- Setup asks a separate question: has the team agreed to agents working in this repo? If not, agents leave the team's
  way of working alone: its AI instructions (`CLAUDE.md`, `AGENTS.md`, `.claude/`), its own docs in the repo and its
  GitLab or GitHub. Where plans live is now only about the plans: a team planning repo is one your teammates read and
  add to; a private one only you see, and nothing links to it.
- Each repo records the LETS version it was set up with. `lets install`, `lets doctor`, `lets where` and the session
  start say when a repo needs `lets setup` again.
- Setup asks which branch work merges into whenever there's a choice (such as `develop` beside `main`).
- `lets sync` runs before commands for any planning repo with a remote, so two computers stay in step.
- `/lets:add` can save a rule for this repo's plans only, including in a private planning repo.
- Issues can go in a private planning repo's own project.
- `/lets:retro` ends with what it saved for your agents, and what it suggests for the team.
- Install always ends with numbered next steps, including trusting the hooks in Codex.
- Every message-length option says it pauses for questions.
- Setup no longer writes a per-repo Claude Code settings file: install's global settings already keep AI attribution
  out. Re-running setup takes the old one out, keeping anything of yours in it.
- The npm package includes Codex's plugin catalogue, so `lets install` can add the plugin to Codex.

## 1.0.1

- LETS recognises your home folder when it's reached through a link (as on macOS), so settings keep their short
  `~/…` paths and still work on another computer.
- Releases are staged on npm, and go public only once a maintainer approves them with two-factor authentication.

## 1.0.0

The first release as a package: `npm install -g @nasiq/lets`, then `lets install`.

- 21 commands in Claude Code and Codex, from planning an epic to closing a change, plus `/lets:patch` for small fixes
  and `/lets:lens` for looking at code through one lens.
- The branch work merges into: `lets setup --base`, `lets note base` for stacked pull requests, shown by `lets where`.
- `lets statusline on` and `off`: LETS's status line in Claude Code at any time, not only at install.
- Optional AI credit (`lets profile ai-credit`, asked at install): never (the default), a trailer in each commit, or a trailer and a pull request note. A repo can choose differently with `lets setup --ai-credit`. When it's on, the guard requires the trailer; branch names never mention an AI.
- Choose where `/lets:learn` saves notes (`lets profile notes`): LETS's folder, a folder of yours, or none. Notes start with front matter saying LETS made them. In a notes folder inside a git repo, the guard stops agents running git; notes made in repos whose team doesn't use LETS leave out the repo's name and use made-up examples.
- `/lets:help` is now `/lets:next`: the board of open work and the one next step. The new `/lets:help` answers questions about LETS itself from its docs.
- `/lets:change-start` takes the work in your own words (`/lets:change-start customers want to track their orders`) and proposes a name; with nothing after it, it asks.
- `/lets:add`: describe a rule in your own words (a commit message format, say) and it becomes an addition to the commands it affects, shown first and saved once you agree.
- Choose which tools LETS is set up in: `lets install` asks once when it finds both Claude Code and Codex (`--tools` answers it), and `lets profile tools` changes it later. `lets doctor` says when a tool is left out by your choice and doesn't count it as a problem.
- Tasks by number or by name (`/lets:build add-order-tracking email-status-changes`), and review comments straight
  into `/lets:change-revise <change> <comment>`.
- Pair mode by default; agent mode per repo or per build (`--agent`), building every remaining task in fresh
  subagents, or in the background (`--bg`).
- Plans in the repo (`plans/`), in a planning repo for the team or a group of repos, or in a private planning repo;
  `lets setup` moves them between homes.
- A guard on every agent command and edit; a status line for Claude Code; `lets profile`, `lets doctor`,
  `lets update`; additions to customise commands without losing them on update.
- Linux and macOS, Python 3.11 or newer.
