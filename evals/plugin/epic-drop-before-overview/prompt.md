---
description: An epic can be dropped before it has an overview, keeping the finding that led to it.
expected_outcome: The map is marked dropped with the reason and a link to prerequisite 01; no overview or changes.
max_turns: 14
allowed_tools: [Read, Glob, Grep, Bash, Skill, Edit, Write]
---

/lets:epic-revise shop-checkout --drop The fee research showed card payments aren't worth it for us. When you're done, run `ls plans/epics/shop-checkout plans/openspec/changes` and `cat plans/epics/shop-checkout/map.md`.
