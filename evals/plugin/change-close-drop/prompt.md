---
description: --drop records the reason and archives the change without touching the living specs.
expected_outcome: The change is archived with a Dropped reason; openspec/specs is unchanged.
max_turns: 14
allowed_tools: [Read, Glob, Grep, Bash, Skill, Edit, Write]
---

/lets:change-close try-dark-mode --drop The design team chose a different theme. When you're done, run `ls plans/openspec/changes plans/openspec/changes/archive plans/openspec/specs` and `cat plans/openspec/changes/archive/*try-dark-mode/proposal.md`.
