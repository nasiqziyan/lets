---
description: --drop asks for one line of why and archives without touching specs.
expected_outcome: Asks why (or uses the given reason); no spec changes.
max_turns: 10
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

/lets:change-close try-dark-mode --drop
