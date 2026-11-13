---
description: A planning command in a repo nobody has set up stops and points to lets setup.
expected_outcome: Says the repo isn't set up and points to lets setup; creates no planning files.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

/lets:change-start add-order-export Let shop owners download their orders as a CSV file.
