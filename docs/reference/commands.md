# Commands you type in Claude Code and Codex

Type them as `/lets:<command>` in Claude Code and `$lets:<command>` in Codex. The agent never starts one on its own.
Every command takes short forms: a unique prefix of a name is enough (`take` for `take-card-payment`, `9` for
prerequisite `09`, `email` for task `email-status-changes`). A task is named by its number or by its heading in
kebab-case.

| Command | Arguments | What it does |
|---|---|---|
| `epic-start` | `<epic> [the idea]` | Chart an epic's map and its first prerequisites |
| `epic-resolve` | `<epic> [prerequisite]` | Resolve one prerequisite (research, grilling, prototype, action) |
| `epic-overview` | `<epic>` | Write the overview for people, ending with the delivery plan |
| `epic-revise` | `<epic> [--drop]` | Take the team's comments on the overview one at a time; or stop the epic |
| `epic-split` | `<epic>` | Turn the overview into changes, checking nothing is lost |
| `change-start` | `[change] [what it's about]` | Plan one pull request in one session of questions, and write its tasks |
| `change-revise` | `<change> [comment]` | Turn review comments or a finding (given here, or pasted when asked) into decisions and tasks |
| `change-close` | `<change> [--drop]` | After approval: update the specs and archive it; or drop it with a reason |
| `patch` | `<what to fix>` | A small fix with no behaviour change, without planning |
| `build` | `<change> [task] [--pair \| --agent] [--bg]` | Build tasks, pairing or in agent mode; draft each commit message |
| `review` | `<change>` | Quick check, standards, the change's acceptance, a doubt pass, weakened gates |
| `walkthrough` | `<change>` | Explain the change in run order, quiz you, then draft the PR description |
| `ideas` | `[the idea]` | Work out what to build when you're not sure yet |
| `learn` | `<concept>` | Learn a concept, in a branch of your session |
| `handoff` | `[what's next]` | Save the session's state to carry on later or in the other tool |
| `pickup` | `[handoff]` | Carry on from a handoff |
| `retro` | `<change>` | Turn a closed change's lessons into standards, glossary, ADRs or checks |
| `next` | `[what I want to do]` | The board of open work and the one next step; or the command for what you describe |
| `help` | `[question about LETS]` | Answers a question about LETS itself from its docs, with the command to run; changes nothing |
| `add` | `[the rule, in your words]` | Adds your own rule to the commands it affects (an addition); shows the lines and saves once you agree |
| `lens` | `[lens] [what to look at]` | Look at the code through one lens and report |

## Lenses

`/lets:lens` alone lists them: `architecture`, `api`, `browser`, `ci`, `constraints`, `frontend`, `launch`,
`migrate`, `observability`, `performance`, `security`, `simplify`. A lens only reports; code it leads to goes through
a patch or a change.

## Helpers

`tdd`, `grilling`, `domain-modeling`, `diagnosing-bugs`, `code-review`, `codebase-design`, `research` and `prototype`
run inside the commands above. They aren't typed.
