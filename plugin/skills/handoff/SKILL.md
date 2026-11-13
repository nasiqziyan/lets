---
name: handoff
description: Save this session's state when I stop part-way, so a fresh session in Claude Code or Codex can pick it up.
argument-hint: "[what the next session is for]"
disable-model-invocation: true
---

1. Read `~/lets/plugin/refs/handoff/SKILL.md` and follow it, except where it says to save: save to
   `.lets/handoffs/<YYYY-MM-DD-HHMM>-<slug>.md` in the planning root, which both Claude Code and Codex can read.
   Handoffs are temporary, so `.lets/` is never committed (`lets setup` keeps it out of git).
2. Reference the change, task, epic or prerequisite in hand by name, name LETS commands as `/lets:<verb>` (Codex:
   `$lets:<verb>`), and end the file with a "Next" section: the exact next step.
3. Finish with: "Pick this up with `/lets:pickup` (Codex: `$lets:pickup`)."
