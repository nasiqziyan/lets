---
name: epic-split
description: Split an epic's overview into tasks, group them into the changes its Delivery section names, check nothing is lost, then create the changes.
argument-hint: "<epic-name>"
---

The epic route, step 4 of 4. Nothing is created until both coverage checks pass and I say yes.

1. The epic is the argument (if missing, list the epics, propose one and wait). Read `epics/<epic>/overview.md`; if it has no Delivery section, stop and suggest
   `/lets:epic-overview`.
2. **Slice the whole overview into tasks, in one pass.** Read `~/lets/plugin/refs/to-tickets/SKILL.md` and use its
   slicing rules (sections 1 to 3) and its quiz (section 4). Ignore its section 5: tasks are written into the changes'
   task lists, not published. Number the tasks across the whole epic.
3. **Assign each task to exactly one change** from the Delivery list. With a group, a change's tasks all touch one
   code repo; a task that needs two repos is a misfit (step 5).
4. **Check coverage, and show me both tables:**
   - Overview → tasks: every user story and every decision in the overview, with the task or tasks that deliver it.
   - Tasks → changes: every task, its change, and what it waits on.
5. **Stop on any misfit** and put it to me: a story or decision with no task; a task that fits no change, or two; a
   task that waits on a task in a later change. I decide (move it, split it, or change a boundary), and you check
   again. Never settle a misfit yourself, even after a general "yes": name the options again and wait.
6. When both tables are clean, show the plan (changes in order, their tasks) and wait for my yes.
7. Name each change as the guide says: short, verb-led, saying what it does, without the epic's name or a number
   (`take-card-payment`, not `shop-checkout-2-payment`). For each, in Delivery order: `openspec new change <name>`,
   add `x-lets-epic: <epic>` to its `.openspec.yaml`, then write its proposal (goal and scope from the
   overview), design (the decisions it carries, linked to their ADRs), deltas (the specs it changes; use
   `openspec instructions` for the formats) and tasks (its tasks, one numbered group each, keeping the epic's task
   titles). With a group, each change is for one code repo: add `x-lets-repo: <repo>` to its `.openspec.yaml`, and
   show each change's repo in the plan. Then `openspec validate <name> --strict`, and fix anything it reports.
8. Check each change as the guide's "Checking a change" says. Add a `## Changes` section to the map listing them in
   delivery order (one `- <change>` line each). **Issues** (optional): offer them as the guide's "Issues" says.
   Commit as the guide says, and end with the first change to build: `/lets:build <change>`. With planning in this repo, say that the epic's files and these change folders are ready
   for me to commit on a branch of their own and merge first (a planning pull request my team can review), so each
   change's branch starts from them.
