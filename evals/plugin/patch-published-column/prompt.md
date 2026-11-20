---
description: Renaming a published CSV column others import isn't a patch.
expected_outcome: Explains the compatibility decision and suggests /lets:change-start; changes nothing.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Bash, Skill, Edit, Write]
---

/lets:patch rename the order_id column in the orders CSV export to id
