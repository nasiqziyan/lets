---
description: --bg is for agent mode only.
expected_outcome: Refuses --bg without --agent, or treats the build as agent mode explicitly; never runs a pairing build in the background.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

/lets:build add-order-export --bg
