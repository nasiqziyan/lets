---
name: change-revise
description: Revise an open change after pull request review comments, or add a finding that belongs to it, as new decisions and tasks.
argument-hint: "<change-name> [comment]"
---

Use this when reviewers ask for changes, or when a lens finds something that belongs in a change that's still open.

1. The change is the argument; if there's none, the one `~/lets/bin/lets note` records for this branch; else list
   the open changes (`openspec list`), propose one, and wait.
2. Anything I gave after the change's name is a review comment or finding: start with it. Otherwise ask me to paste
   the review comments or the finding. In a repo that isn't mine you can't read its forge; never try.
3. Take them **one at a time**, as a short grilling (call the Skill tool with "grilling"):
   - **Agree**: record the decision in the change's design (and its deltas when behaviour changes), and add a task
     for it, numbered after the existing ones.
   - **Disagree**: no task. Draft a short reply giving my reason, for me to post.
   - **Partly**: settle what we will do, then as agree.
   - **New work** that doesn't belong to this change: note it as out of scope and suggest `/lets:change-start` for it
     later.
4. Run `openspec validate <change> --strict`, then check the change as the guide's "Checking a change" says. Show me
   what changed in the tasks (only that) and the drafted replies.
5. Commit planning files as the guide says. End with the first new task: `/lets:build <change> <task>`, reminding me
   that the walkthrough afterwards only covers the files changed since my last one.
