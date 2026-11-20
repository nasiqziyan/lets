# Settings and files

## Per repo (git config, in the repo's own `.git/config`)

| Key | Values | Set by |
|---|---|---|
| `lets.kind` | `own` (full use: your repo, or the team has agreed) or `other` (individual use: agents change nothing the team sees: its AI instructions, docs and GitLab/GitHub) | `lets setup` ("How should LETS work…?", or `--use`) |
| `lets.version` | the LETS release whose setup questions this repo was set up with | `lets setup` |
| `lets.plans` | the planning repo, as `~/...` (unset: plans in `plans/`) | `lets setup` |
| `lets.sharing` | `team` or `private` | `lets setup` |
| `lets.build` | `pair` or `agent` | `lets setup` |
| `lets.tests` | `propose`, `always` or `ask` | `lets setup` |
| `lets.agents` | `local`, `commit` or `ship`: how far agents may go with git | `lets setup` |
| `lets.check` | the quick check, such as `npm run -s check` | `lets setup` |
| `lets.repo` | the repo's name in a group | `lets setup` |
| `lets.base` | the branch work here merges into, when it can't be detected (unset: the remote's default branch, else the usual trunk the branch split from) | `lets setup` (it asks only when it can't tell), or `--base` |
| `lets.note-examples` | `real` (the default) or `made-up`: the examples in learning notes made in this repo | `lets note examples made-up` (an agent runs it when you ask for made-up examples) |
| `lets.ai-credit` | `never`, `trailer:<line>` or `trailer-pr:<line>` (unset: your profile's answer) | `lets setup --ai-credit` |
| `branch.<name>.lets-change`, `.lets-patch`, `.lets-mode` | what the branch is for, and the mode | `lets note` (the building commands) |
| `branch.<name>.lets-base` | the branch this one merges into, for stacked pull requests; wins over `lets.base` | `lets note base <branch>` |
| `branch.<name>.lets-reviewed`, `.lets-walked` | the commit reviewed, and walked through | `/lets:review`, `lets walkthrough complete` |
| `branch.<name>.letsAllow` | a finding you approved on this branch | you |

A planning repo has `lets.role planning`.

## Files LETS keeps

| Where | What | Travels between computers? |
|---|---|---|
| `~/.config/lets/profile.md` | your profile | yes |
| `~/.config/lets/config.json` | where planning repos are kept, which tools LETS is set up in, your learning-notes folder, your own status line while LETS's is on, the code repos you set up, the version last wired up | yes |
| `~/.config/lets/additions/` | your additions to commands | yes |
| `~/.local/state/lets/backups/` | each file LETS edited, as it was before | no |
| `~/.local/state/lets/logs/` | details of unexpected errors | no |
| `~/.local/state/lets/host-settings.json` | which Claude Code settings LETS changed and what they were before, so `lets uninstall` puts back yours | no |
| `~/.local/share/lets/learning/` | notes from `/lets:learn`, unless you chose a folder of yours (`lets profile notes`) | your choice |
| `~/.cache/lets/update.json` | when LETS last checked for a new version | no |
| `~/lets` | a link to the installed package; every installed file points through it | made by `lets install` |

## Files outside LETS it edits (shown and agreed first)

`~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` (a marked block), `~/.claude/settings.json` (attribution off, the
folders agents may write, the status line if you chose it), `~/.codex/hooks.json` and `~/.codex/config.toml`, and
links in `~/.claude/skills/lets` and `~/.local/bin`.
