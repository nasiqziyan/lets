# Let the agent build (agent mode, and in the background)

Each repo has a build mode, set at `lets setup` (`pair` or `agent`). Any build can override it:

```text
/lets:build take-card-payment 2 --agent    the agent builds task 2, then walks you through it
/lets:build take-card-payment --agent      the agent builds every remaining task, each in a fresh subagent
/lets:build take-card-payment --pair       pair on the next task, whatever the repo's mode
```

With no task number in agent mode, it builds the tasks in order, checks each one's evidence (tests, type check,
build), and stops at the first failure, question or decision.

## In the background

```text
/lets:build add-gift-cards --agent --bg
```

`--bg` runs the build as a background session in its own worktree, using the tool's own background sessions (Claude
Code's `claude --bg`; in Codex, a new thread in the app). It's allowed only in agent mode, and only for a change whose
"waits on" changes are already merged, so two background builds never step on each other. `/lets:next` lists
background builds on its board. The walkthrough is still yours before the pull request.
