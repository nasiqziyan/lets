---
name: epic-resolve
description: Resolve one prerequisite of an epic (research, grilling, prototype or action), record the decision on the map, and add any new prerequisites it uncovers.
argument-hint: "<epic-name> [prerequisite number, or research]"
disable-model-invocation: true
---

The epic route, step 2 of 4: run once per prerequisite, one per session. Research prerequisites can go together:
`/lets:epic-resolve <epic> research` starts every ready one.

1. The epic is the argument's first word. If I gave none, list the epics under `epics/` and ask which; if there's
   only one, propose it and wait for my yes.
2. Choose the prerequisite:
   - If I gave a number, use it. If it waits on an unresolved prerequisite, name that one and stop.
   - If I said `research`, take every ready research prerequisite.
   - Otherwise list the ready prerequisites (number, title, type), recommend one, and wait for my yes.
   - Also list any claimed prerequisite with no answer, as the guide's "Two sessions at once" says, so one whose
     session was closed doesn't stay stuck.
3. Read `~/lets/plugin/refs/wayfinder/SKILL.md` and follow its **Work through the map** mode for that prerequisite,
   with the epic files as the tracker:
   - **research**: start it as the guide's "Research in the background" says; findings go to
     `research/<topic>.md`. If it can't run in the background, call the Skill tool with "research" and do it here.
   - **grilling**: call the Skill tool with "grilling" and "domain-modeling"; ask the way my profile says (one
     decision at a time, or in rounds).
   - **prototype**: call the Skill tool with "prototype"; keep it throwaway and link it from the answer.
   - **action**: something I do outside (send an email, get access). Give me a precise checklist; when the action
     needs someone else's answer, draft a questionnaire with me (`~/lets/plugin/refs/to-questionnaire/SKILL.md`),
     saved as `questionnaires/<slug>.md`, written as from me (no mention of AI or agents). Resolve it only when I
     come back with the outcome.
4. Record it: the answer in the prerequisite file, the gist on the map, an ADR in `docs/adr/` for a decision a future
   reader would question, and new terms in `GLOSSARY.md`.
5. Add any new prerequisites it uncovered and graduate fog from "Not yet specified", and tell me about each one. Start
   any new research prerequisite in the background, as in step 3.
6. Commit as the guide says, then end as its "Ending a step" says: what's ready next, or, when nothing is left open,
   `/lets:epic-overview <epic>`.
