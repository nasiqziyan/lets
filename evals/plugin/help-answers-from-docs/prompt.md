---
description: "/lets:help answers a question about LETS from its docs, with the command to run, and changes nothing."
expected_outcome: "Says to re-run `lets setup` in the repo and choose another answer to where the plans live; changes nothing."
max_turns: 8
allowed_tools: [Read, Glob, Grep, Bash, Skill]
---

/lets:help how do I move my plans to a planning repo?
