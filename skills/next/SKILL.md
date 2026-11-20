---
name: next
description: Show the open work here (epics, changes, patches, background builds) and recommend the one LETS command that fits next. With a description of what I want to do, recommend the command for it. It never runs them.
argument-hint: "[what I'm trying to do]"
---

**With no argument: the board.** From `~/lets/bin/lets where`, `~/lets/bin/lets note`, `git status` and the planning
root, show a short board, then the one next step:

```text
Epics      shop-checkout   ●◉○○  2 of 4 changes merged · next: take-card-payment
Changes    take-card-payment   ●●◉○  task 3 of 4 · this branch
           add-gift-cards      ○○○   not started
Patch      fix-typo-in-footer   this branch has none
Background add-staff-admin   building task 2 (agent mode)
Next       /lets:build take-card-payment 3   (task 3: Validate the card number)
```

Leave out empty rows. Changes come from `openspec list`, their task dots from each `tasks.md` (● done, ◉ next, ○ to
come), epics from `epics/*/map.md` (its `## Changes` list, in order; archived changes are merged). Background builds
are the tool's own background sessions, if any. Then recommend **one** command with one line of why, and don't run it.

**With what I want to do: the table.** Recommend one command with one line of why, and the one after it. Don't run either.
In Codex, commands are typed `$lets:<command>`.

| I want to | Command |
|---|---|
| Work out what to build when I'm not sure yet | `/lets:ideas` |
| Plan something big and unclear (several pull requests) | `/lets:epic-start`, then `/lets:epic-resolve` once per prerequisite, `/lets:epic-overview`, `/lets:epic-split` |
| The team commented on an epic's overview, or plans changed | `/lets:epic-revise` (`--drop` to stop an epic) |
| Plan one piece of work (one pull request) | `/lets:change-start` |
| Fix or tidy something without changing behaviour | `/lets:patch` |
| Build a change's tasks | `/lets:build` (`--agent` for agent mode, `--bg` in the background) |
| Review the work so far | `/lets:review` |
| Be walked through the change, and get the pull request description | `/lets:walkthrough`, then `! lets walkthrough complete` |
| Reviewers asked for changes, or a finding belongs to an open change | `/lets:change-revise` |
| The pull request is approved: update the specs before merging | `/lets:change-close` |
| Not doing a change after all | `/lets:change-close <change> --drop` |
| Learn a concept that came up (in a branch of the session) | `/branch` (Codex `/fork`), then `/lets:learn` |
| Stop here and continue in a fresh session or the other tool | `/lets:handoff`, then `/lets:pickup` |
| Turn a closed change's mistakes into standards and checks | `/lets:retro` |
| Look at the codebase through a lens | `/lets:lens <name>` (`/lets:lens` lists them) |
| Set up a repo, change how it's set up, or change my answers | in a terminal: `lets setup`, `lets profile` |

Helpers (tdd, grilling, diagnosing-bugs, research, prototype and the rest) aren't commands: they run inside the
commands above, so never suggest one as `/lets:<helper>`. A lens only reports: code work it leads to goes through a
change. Quick side question: `/btw` (Claude Code), `/side` (Codex).
