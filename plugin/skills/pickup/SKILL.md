---
name: pickup
description: "Continue from a saved handoff: summarise where things stood and carry on from its Next section."
argument-hint: "[handoff file]"
disable-model-invocation: true
---

1. If I named a handoff, use it. Otherwise list the files in `.lets/handoffs/` in the planning root, newest first (date and
   title), propose the newest, and wait for my yes.
2. Read it, summarise it in five lines, and check it against the repo now (the branch, and whether the files it
   names have changed since). Say if anything has moved on.
3. Continue from its "Next" section, using the LETS command it names.
