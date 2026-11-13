---
description: "/lets:next on a typo: no behaviour changes, so it should recommend /lets:patch."
expected_outcome: "Recommends /lets:patch with one line of why; doesn't start the work."
max_turns: 6
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

/lets:next There is a typo in the footer: "Copyrite". What should I run?
