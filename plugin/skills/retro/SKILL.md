---
name: retro
description: Look back at a closed change and turn its mistakes into standards, glossary entries, ADRs or checks, so they don't recur.
argument-hint: "<change-name>"
disable-model-invocation: true
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
   - A lesson an automatic check could catch (a lint rule, a test, a CI step) belongs in the code repo. Where the
     team has agreed to agents (`lets where`: team), make it on a branch of its own for a merge request; otherwise
     don't change the code repo: write it up for me to raise with the team.
   - If the LETS guard should have caught a mistake, say so, and draft an issue for LETS describing the case.
4. End with two sections, in plain words:
   - **Saved for your agents**: each planning-root file you changed, with the exact lines added.
   - **For the team** (if any lesson is for them): the check, the exact config change, and a short message I could
     post to the team or put in a merge request; where the team has agreed, the branch it's on instead.
5. Commit planning files as `~/lets/guides/planning.md` says.
