---
description: epic-split creates nothing before the coverage checks pass and the user says yes.
expected_outcome: Shows tables / asks, creates no changes.
max_turns: 15
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

/lets:epic-split shop-checkout
