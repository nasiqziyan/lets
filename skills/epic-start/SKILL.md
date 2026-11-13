---
name: epic-start
description: Start an epic (work too big for one pull request, with a lot still undecided) by charting its map and its first prerequisites.
argument-hint: "<epic-name> [the idea]"
---

The epic route, step 1 of 4: `epic-start` → `epic-resolve` (once per prerequisite) → `epic-overview` → `epic-split`.

1. The argument's first word is the epic's name (lowercase, hyphens: `shop-checkout`); it becomes `epics/<name>/`. If
   I gave no name, ask for one and wait. If `epics/<name>/` already exists, say so and suggest
   `/lets:epic-resolve <name>` instead.
2. Read what I've gathered: `epics/<name>/inputs/` if it exists, and anything I pass or paste.
3. Read `~/lets/plugin/refs/wayfinder/SKILL.md` and follow its **Chart the map** mode, with the epic files in
   `~/lets/guides/planning.md` as the tracker. The destination is always: an overview, then the changes (one per pull
   request) that deliver it.
4. Always include a grilling prerequisite named "Where do the pull requests split?": the boundaries between the
   changes, each one a pull request that can be reviewed and merged on its own. It waits on whatever it needs.
5. If charting shows the work fits in one pull request, stop and say so: suggest `/lets:change-start` instead.
6. Commit as `~/lets/guides/planning.md` says, then end with the number of prerequisites, which are ready now, and the
   next command: `/lets:epic-resolve <name>`.
