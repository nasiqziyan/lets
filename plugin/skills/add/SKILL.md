---
name: add
description: Add my own rule to how LETS commands work, described in my own words (such as a commit message format). Works out which commands it affects, shows the exact lines, and saves them once I agree.
argument-hint: "[the rule, in my own words]"
disable-model-invocation: true
---

An addition is a Markdown file named after a command: the agent follows it after that command's own steps, and it
wins where they differ, but never over the guard. This command writes them for me, so I never need to know the files.

1. **No rule given:** ask what I'd like LETS to do differently, and wait.
2. **Work out which commands it affects.** Read the commands' own steps (`~/lets/plugin/skills/<command>/SKILL.md`)
   to find where the rule applies: a commit message format, for example, affects `build` and `patch`, which draft
   commit messages. Name each command and say why in a few words.
3. **Ask whose it is:** just mine, in every repo (`~/.config/lets/additions/<command>.md`), or the team's, for
   everyone working on this repo's plans (`additions/<command>.md` in the planning root `lets where` prints). Offer
   the team's only when `lets where` says the plans are shared with the team.
4. **Show the exact lines** for each file: short, imperative, one rule per line, specific enough to follow without
   guessing (an example helps). If the file already exists, read it: say if the new rule repeats or contradicts one
   already there, and show where the new lines go. Then ask whether to save, and wait.
5. **Save** only once I agree, adding to each file (create it if needed). Never write a rule that weakens a gate,
   skips a check or tells agents to get past the guard: say why and stop. A team addition is a planning file:
   commit it as the planning guide says.
6. Finish with the files changed, and that the rule applies from the next time each command runs.
