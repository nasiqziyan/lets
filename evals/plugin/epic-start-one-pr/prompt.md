---
description: If the work fits one pull request, epic-start stops and suggests change-start.
expected_outcome: "Suggests /lets:change-start."
max_turns: 10
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

/lets:epic-start fix-footer The footer has a typo.
