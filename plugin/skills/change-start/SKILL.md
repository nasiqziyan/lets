---
name: change-start
description: Plan one change (one pull request) in a single grilling session, from a tiny bug fix to a feature, and create it with its tasks.
argument-hint: "[change-name] [what it's about]"
disable-model-invocation: true
---

The default route: one session of questions, then one change with its tasks, ready to build. Every piece of work,
however small, is a change.

1. If the argument starts with a change name (one word in kebab-case, such as `add-order-export`), that's the change's
   name and the rest says what it's about. Otherwise the whole argument says what it's about: propose a name (short,
   starting with a verb, saying what the work does, as the guide says) and wait. With no argument, ask what I want to
   build. Run it from the code repo the change is for (or, in a group folder, ask which repo). If the change
   already exists, say so and suggest `/lets:build` or `/lets:change-revise`. If it changes no behaviour at all,
   suggest `/lets:patch` instead.
2. Read the context: the code it touches, `GLOSSARY.md`, the related specs (`openspec list --specs`) and ADRs.
3. **A bug whose cause isn't known:** call the Skill tool with "diagnosing-bugs" and follow it until we know the cause,
   and show me the evidence, before any other question.
4. **Grill me**, the way my profile says (one decision at a time, or in rounds): call the Skill tool with "grilling"
   and "domain-modeling". Record decisions as we go (an ADR for one a future reader would question, new terms in
   `GLOSSARY.md`). When the work touches an area a lens covers (security, performance, api, frontend, observability,
   ci, migrate), read it (`~/lets/plugin/refs/<lens>/SKILL.md`) and use its guidance in the questions. A small fix may need one question,
   or none.
5. Research or a prototype happens here, in this session (call the Skill tool with "research" or "prototype"). What
   can't be settled goes into the change as an assumption, written as one.
6. **If it needs more than one pull request**, stop and recommend the epic route, saying why. If I accept, read
   `~/lets/guides/planning.md` and write `epics/<change-name>/map.md` from this session: the decisions so far, and
   each open question as a prerequisite. Then suggest `/lets:epic-resolve <change-name>` and stop. If I reject, carry
   on as one change.
7. **Slice it into tasks:** read `~/lets/plugin/refs/to-tickets/SKILL.md` and use its slicing rules and quiz
   (sections 1 to 4, not 5). Check coverage: every decision lands in at least one task. Show me the tasks and wait for
   my yes.
8. **Create it.** With plans in this repo, the change's folder rides in its pull request, so first propose a branch
   for it (named after the change; the name is mine to choose), create it from the base when I agree, and record it
   (`~/lets/bin/lets note change <name>`). Then
   `openspec new change <name>`; write the proposal, the design (when there are decisions to record), the deltas (or
   `skip_specs: true` when no behaviour changes) and the tasks, one numbered group per task; use
   `openspec instructions` for the formats. With a group (`lets where` prints a group), add `x-lets-repo: <repo>` to
   the change's `.openspec.yaml`: the one code repo it changes; work in two repos is two changes. Run
   `openspec validate <name> --strict` and fix what it reports.
9. **Check the change** as the guide's "Checking a change" says, and fix what it finds with me.
10. **Issues** (optional): offer them as the guide's "Issues" says.
11. Commit as the guide says, and end with `/lets:build <change-name>`.
