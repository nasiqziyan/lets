---
description: epic-resolve ends by naming the next step for a fresh session, not by offering to carry on.
expected_outcome: "Records 02, then says start a fresh session and run /lets:epic-resolve shop-checkout 03."
max_turns: 20
allowed_tools: [Read, Glob, Grep, Bash, Skill, Edit, Write]
---

/lets:epic-resolve shop-checkout 02 I've done it: the payment provider confirmed we can take cards and Apple Pay, with test keys by Friday.
