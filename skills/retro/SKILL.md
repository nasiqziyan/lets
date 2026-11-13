---
name: retro
description: Look back at a closed change and turn its mistakes into standards, glossary entries, ADRs or checks, so they don't recur.
argument-hint: "<change-name>"
---

1. The change is the argument; if missing, list the recently closed changes
   (`openspec/changes/archive/`, newest first), propose the latest, and wait.
2. Read the change: its decisions, its tasks (including those `/lets:change-revise` added after review), and any
   review comments or fixes we went through in this session.
3. Read `~/lets/plugin/refs/retro/SKILL.md` and follow it, with these LETS rules:
   - Propose lessons one at a time; I accept or reject each.
   - Lessons go into files in the planning root (`CODING_STANDARDS.md`, `CONSTRAINTS.md`, `GLOSSARY.md`,
     `docs/adr/`), never into agent memory: I switch between Claude Code and Codex.
   - For a coding standard, draw on the checklists in `~/lets/plugin/refs/checklists/`.
   - Where the plans are private, a check that belongs in the team's CI or linters is a suggestion for me to
     raise with the team, not a change you make.
   - If the LETS guard should have caught a mistake, say so, and draft an issue for LETS describing the case.
4. Commit planning files as `~/lets/guides/planning.md` says.
