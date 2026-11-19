---
description: Given only a name, epic-start creates inputs/, gives its full path, and asks for the description.
expected_outcome: "Creates plans/epics/shop-checkout/inputs/, shows its path, asks me to describe the work; no map yet."
max_turns: 10
allowed_tools: [Read, Glob, Grep, Bash, Skill, Write]
---

/lets:epic-start shop-checkout
