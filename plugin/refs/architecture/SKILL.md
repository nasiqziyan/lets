---
name: architecture
description: A lens on the codebase's design. Find deepening opportunities (shallow modules, leaky seams), report them, then grill through the one I pick.
---

A lens: it reports and advises; it never changes code.

1. Run `~/lets/bin/lets where`.
2. Read `~/lets/plugin/refs/improve-architecture/SKILL.md` and follow it. Where it says to call the Skill tool for
   "codebase-design", do so. Glossary terms and ADRs it records go in the planning root.
3. Save the report as `research/architecture-<YYYY-MM-DD>.md` in the planning root, and commit planning files as
   `~/lets/guides/planning.md` says.
4. End by suggesting the next step for the opportunity we chose: `/lets:change-start <name>` for one pull request,
   `/lets:epic-start <name>` for more, or `/lets:change-revise <change>` if it belongs to a change that's still open.
