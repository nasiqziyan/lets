---
description: "/lets:add turns a rule in plain words into additions for the commands it affects, and asks before saving."
expected_outcome: "Names build and patch (they draft commit messages), shows the exact lines, and waits before writing."
max_turns: 8
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

/lets:add every commit message should start with the ticket number, like ABC-123: Add order tracking
