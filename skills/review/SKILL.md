---
name: review
description: Review everything a change's branch has so far (the quick check, standards, the change's acceptance and deltas, a doubt pass, weakened gates) and pair on the fixes.
argument-hint: "<change>"
---

Review everything the branch changes, committed or not, against where it left the base branch.

1. The change is the argument; if there's none, the one `~/lets/bin/lets note` records for this branch; else propose
   one and wait. (Patches too: review the branch, with the patch's own description as its "change".)
2. **Gates and the quick check.** Run `~/lets/bin/lets check --run`. Each item it lists switches a check off or loosens
   one: each is a finding. A failing quick check is a must-fix finding.
3. **Standards and the change.** Call the Skill tool with "code-review" and follow it, including on uncommitted work.
   - Its "change" is this change: `proposal.md`, `design.md`, the deltas under `specs/` and `tasks.md`.
   - Give the standards reviewer `CODING_STANDARDS.md` and `CONSTRAINTS.md` from the planning root (and the code
     repo's own, which win where they disagree), the five axes in `~/lets/plugin/refs/quality/SKILL.md`, and the
     checklists in `~/lets/plugin/refs/checklists/` the change touches. Also look for code that is harder to read
     than it needs to be (`~/lets/plugin/refs/simplify/SKILL.md`).
   - Check that the deltas still describe what the code now does.
4. **Doubt.** Pick the one to three riskiest decisions (an error path, a data or API contract, concurrency, security,
   anything irreversible) and give each the fresh-context adversarial review in `~/lets/plugin/refs/doubt/SKILL.md`.
5. **Report** one table: finding, severity, file and line, why. Verify each finding against the code first; drop the
   ones that don't hold up. **Must fix** only for: incorrect behaviour, an unmet requirement or scenario, or a
   weakened gate. Style and taste are at most **consider**; the rest is **should fix**.
6. Pair on the fixes (`~/lets/plugin/skills/build/pairing.md`): I fix them unless I hand one to you. When nothing must
   be fixed, say so plainly, record it with `~/lets/bin/lets note reviewed`, and give the next step: the next task
   (`/lets:build <change>`), or `/lets:walkthrough <change>` after the last.
