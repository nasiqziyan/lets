---
name: epic-resolve
description: Resolve one prerequisite of an epic (research, grilling, prototype or action), record the decision on the map, and add any new prerequisites it uncovers.
argument-hint: "<epic-name> [prerequisite number]"
disable-model-invocation: true
---

The epic route, step 2 of 4: run once per prerequisite, one per session (research prerequisites may be resolved
together).

1. The epic is the argument's first word. If I gave none, list the epics under `epics/` and ask which; if there's
   only one, propose it and wait for my yes.
2. Choose the prerequisite:
   - If I gave a number, use it. If it waits on an unresolved prerequisite, name that one and stop.
   - Otherwise list the ready prerequisites (number, title, type), recommend one, and wait for my yes.
3. Read `~/lets/plugin/refs/wayfinder/SKILL.md` and follow its **Work through the map** mode for that prerequisite,
   with the epic files as the tracker:
   - **research**: call the Skill tool with "research"; findings go to `research/<topic>.md`.
   - **grilling**: call the Skill tool with "grilling" and "domain-modeling"; ask the way my profile says (one
     decision at a time, or in rounds).
   - **prototype**: call the Skill tool with "prototype"; keep it throwaway and link it from the answer.
   - **action**: something I do outside (send an email, get access). Give me a precise checklist; when the action
     needs someone else's answer, draft a questionnaire with me (`~/lets/plugin/refs/to-questionnaire/SKILL.md`),
     saved as `questionnaires/<slug>.md`, written as from me (no mention of AI or agents). Resolve it only when I
     come back with the outcome.
4. Record it: the answer in the prerequisite file, the gist on the map, an ADR in `docs/adr/` for a decision a future
   reader would question, and new terms in `GLOSSARY.md`.
5. Add any new prerequisites it uncovered and graduate fog from "Not yet specified", and tell me about each one.
6. Commit as the guide says. End with what's ready next, or, when nothing is left open,
   `/lets:epic-overview <epic>`.
