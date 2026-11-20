---
description: A small, clear visible edit stays a patch.
expected_outcome: Treats it as a patch (proposes a branch or makes the edit), without sending it to /lets:change-start.
max_turns: 10
allowed_tools: [Read, Glob, Grep, Bash, Skill, Edit, Write]
---

/lets:patch rename the "Buy" button on the orders page to "Add to basket". It does exactly the same thing.
