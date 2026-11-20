---
name: epic-overview
description: Write an epic's overview, the readable document for people, once every prerequisite on its map is resolved.
argument-hint: "<epic-name>"
disable-model-invocation: true
---

The epic route, step 3 of 4.

1. The epic is the argument (if missing, list the epics, propose one and wait).
2. If any prerequisite is still open or claimed, list them and stop.
3. Read the map, every resolved prerequisite, the research files they link and the ADRs they made.
4. Read `~/lets/plugin/refs/to-spec/SKILL.md` and follow it to write `epics/<epic>/overview.md` in its overview
   template, with these LETS differences:
   - Don't publish anywhere and apply no labels: the file is the overview.
   - Implementation and testing decisions come from the map's Decisions so far; link each to its prerequisite or ADR.
   - When the epic's inputs include a diagram or plan the work departs from, add **Where we differ from the diagram**:
     each difference and why.
   - End with **Delivery**: the changes from "Where do the pull requests split?", in order, one per pull request, each
     with a name (short and verb-led, as the guide says: `add-cart-api`), a goal in one line, and what it waits on.
5. Write for people who weren't in the sessions: define terms on first use, no session talk, nothing that names an
   AI.
6. Commit as the guide says. Tell me the overview is ready to read and share, then end as the guide's "Ending a
   step" says, with `/lets:epic-split <epic>`. If the team comments on it, `/lets:epic-revise <epic>` takes the
   comments one at a time.
