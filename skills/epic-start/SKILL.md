---
name: epic-start
description: Start an epic (work too big for one pull request, with a lot still undecided) by charting its map and its first prerequisites.
argument-hint: "<epic-name> [the idea]"
---

The epic route, step 1 of 4: `epic-start` → `epic-resolve` (once per prerequisite) → `epic-overview` → `epic-split`.

1. **The name first.** The argument's first word is the epic's name (lowercase, hyphens: `shop-checkout`); it
   becomes `epics/<name>/`. If I gave no name, ask for the name only, nothing else, and wait.
2. An epic has started once `epics/<name>/map.md` exists. If it does, say so and suggest
   `/lets:epic-resolve <name>`, then stop. A folder holding only `inputs/` hasn't started.
3. Create `epics/<name>/inputs/` if it isn't there.
   - If I gave only the name, tell me the folder's full path and ask me to describe the problem (what I want, what's
     decided, what isn't), and to put any notes, specs or diagrams in that folder or tell you where they are. Then
     wait until I say I'm ready.
   - If I gave a description too, mention the folder and its full path in one line, and carry on.
4. Read everything in `inputs/` and everything I pass, paste or point to. Copy files I point to into `inputs/`;
   never move, change or delete the originals.
5. Read `~/lets/plugin/refs/wayfinder/SKILL.md` and follow its **Chart the map** mode, with the epic files in
   `~/lets/guides/planning.md` as the tracker. The destination is always: an overview, then the changes (one per pull
   request) that deliver it. One difference: research runs alongside the conversation, not at the end. As soon as
   the charting turns up a research question that needs nothing more from me, write it as a prerequisite and start
   it as the guide's "Research in the background" says, then carry on charting.
6. Always include a grilling prerequisite named "Where do the pull requests split?": the boundaries between the
   changes, each one a pull request that can be reviewed and merged on its own. It waits on whatever it needs.
7. If charting shows the work fits in one pull request, stop and say so: suggest `/lets:change-start` instead.
8. Commit as `~/lets/guides/planning.md` says, then end as its "Ending a step" says, with the number of
   prerequisites and the next command, `/lets:epic-resolve <name> <number>`.
