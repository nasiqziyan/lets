---
description: "/lets:build with no change and no branch note lists open changes and waits."
expected_outcome: Lists candidates (or says there are none / not set up) and asks; builds nothing.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Bash, Skill, Edit, Write]
---

/lets:build
