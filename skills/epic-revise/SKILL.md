---
name: epic-revise
description: Revise an epic's overview after the team's comments on it, one comment at a time, before or after it is split into changes.
argument-hint: "<epic> [--drop]"
---

Use this when people have read an epic's overview and come back with comments: in a meeting, a chat, or on the
planning pull request.

1. The epic is the argument (if missing, list the epics that have an overview, propose one and wait). Read the
   overview, the map and its resolved prerequisites.
   **With `--drop`** the epic is stopped: ask for one line of why, drop each of its open changes as
   `/lets:change-close <change> --drop` does, mark the map `Dropped: <why>` under its title, commit as the guide says,
   and stop.
2. Ask me to paste the comments, with who made each one if it matters. In a repo whose plans are private you can't
   read its forge; never try.
3. Take them **one at a time**, as a short grilling (call the Skill tool with "grilling"). For each, say what it
   touches (a user story, a decision and its prerequisite, the Delivery list) and propose one of:
   - **Agree, and it's a wording or a detail**: update the overview.
   - **Agree, and it changes a decision**: reopen that prerequisite (set `Status: open`, and add the comment under
     `## Comment`, with who made it), then resolve it again with me here, as `/lets:epic-resolve` would. Update the
     map's Decisions so far, any ADR it made, and the overview.
   - **Disagree**: change nothing, and draft a short reply giving my reason, for me to post.
   - **Partly**: settle what we will do, then as agree.
   - **New work** that doesn't belong to this epic: add it to the map's Out of scope, and suggest
     `/lets:change-start` or `/lets:epic-start` for it later.
   Wait for my answer on each before the next.
4. **If the epic is already split** (the map has a Changes section), each agreed change goes to the change it lands
   in: say which, and update that change's design, deltas and tasks as `/lets:change-revise` would. A change that is
   already merged can't be revised: suggest a new change for it instead, and add it to the map's Changes.
5. If the Delivery list changed and the epic isn't split yet, say so: `/lets:epic-split` will use the new list.
6. Show me what changed (the overview's sections, reopened prerequisites, changes touched) and the drafted replies.
   Run `openspec validate <change> --strict` for each change touched. Commit as the guide says, and end with the next
   step: share the updated overview, or `/lets:epic-split <epic>`, or `/lets:build <change> <task>`.
