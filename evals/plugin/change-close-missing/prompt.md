---
description: Closing a change that doesn't exist says so clearly and changes nothing.
expected_outcome: A clear message that there's no such change; no files edited, nothing archived.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Bash, Skill, Edit, Write]
---

/lets:change-close try-neon-mode --drop We changed our minds.
