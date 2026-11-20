---
name: build
description: Build a change's tasks, pairing by default (I write the code, you guide and check it), or in agent mode. Drafts each task's commit message.
argument-hint: "<change> [task] [--pair | --agent] [--bg]"
disable-model-invocation: true
---

A task is one numbered group in the change's `tasks.md`. Pairing builds one task per session.

**Before any code**

1. Find the change: the argument's first word. If there's none, run `~/lets/bin/lets note`: a change recorded for
   this branch is the one. Otherwise, if exactly one open change's name appears in the branch name, take it. Otherwise
   list the open changes (`openspec list`), propose one, and wait.
2. **The mode.** `--pair` or `--agent` if I gave one, else this repo's build choice (`lets where` prints it).
3. **The branch.** One change is one pull request, so one branch. If I'm on a shared branch (`main`, `master`,
   `develop`, the default branch), propose a branch named after the change and wait: the name is mine to choose.
   Create it from the base (the branch `lets where` prints as `base`), or switch to it if it exists. Then record it:
   `~/lets/bin/lets note change <change> --mode <pair|agent>`.
4. **The task.** The one I gave, by its number (`2`), its name (its heading in kebab-case: `email-status-changes` for
   `## 2. Email status changes`) or a unique start of either; if several match, list them and ask; if none, list the
   tasks. Else the first task not done. If it depends on an unfinished task, say which and
   stop. Read the change: proposal, design, the deltas' scenarios (its acceptance) and the task's steps.
5. **Test-first**, by this repo's choice: `propose`: propose test-first or not for this task, with one line of why,
   and wait. `always`: test-first. `ask`: not unless I ask.
6. When the task touches an area a lens covers (security, performance, api, frontend, observability, browser, ci,
   migrate), read it (`~/lets/plugin/refs/<lens>/SKILL.md`) and apply it as we go. Check any API or library use
   against its official docs (`~/lets/plugin/refs/sources/SKILL.md`).

**Pair mode** (one task)

- Read `~/lets/plugin/skills/build/pairing.md` now and follow it.
- Test-first: call the Skill tool with "tdd" for its loop. You write the failing test and run it, and show me it
  fails for the right reason (red). Then we pair on the code that makes it pass (I write it, unless I hand it over).
  Run it green, and carry straight on to the next test without stopping to ask.
- When a concept is new to me, suggest a detour (`/branch` or `/fork`, then `/lets:learn <concept>`).

**Agent mode**

- With a task: you build that task, then walk me through it slice by slice before we call it done.
- With no task: build every remaining task in order, each in a fresh subagent given the change folder, the
  task, and this file's rules (where the tool has no subagents, build one task and tell me to start a fresh session
  for the next). After each, check its evidence yourself (below). Stop at the first failure, question or decision,
  and tell me where things stand.
- `--bg` (agent mode only): run it as a background session in its own worktree, by the tool's own means (Claude Code:
  `claude --bg`; Codex: a new thread in the app). Only for a change whose "waits on" changes are all merged: if one
  isn't, say which and stop. Tell me how to check on it. The walkthrough is still mine before the pull request.

**Each task is done when**

- You show the output that proves it: the task's tests, the type check, the build (the full suite after the last
  task). Never claim done without it. Tick its steps in `tasks.md`.
- You draft its commit message in a code block I can copy: a subject that says what changed, a short body saying why
  (matching `git log --oneline -20`; `~/lets/plugin/refs/git/SKILL.md` where the repo has no convention). If the work
  merges or removes tests or changes a check's configuration, the body says why. No mention of AI or agents, except
  the trailer `lets where` shows as the AI credit, if any. I commit, unless `lets.agents` is `commit` or `ship` and I asked you to.
- Then suggest `/lets:review <change>`; after the last task, `/lets:walkthrough <change>`.
