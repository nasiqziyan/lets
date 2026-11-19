---
description: A folder holding only inputs/ is not a started epic; epic-start reads the inputs.
expected_outcome: "Doesn't call the epic started; reads inputs/notes.md."
max_turns: 10
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

/lets:epic-start shop-checkout
