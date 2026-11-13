---
name: learn
description: Teach me one concept that came up in my work, as a short curriculum in dialogue, then save a note if I want one.
argument-hint: "<concept>"
disable-model-invocation: true
---

This is a teaching detour. It belongs in a branch of my session (`/branch` in Claude Code, `/fork` in Codex) so my main
session stays clean: if I ran it in my main working session, say so in one line and ask whether to continue anyway.
If I passed no concept, ask which. Don't edit any project files in this session. Teach the way my profile's teaching
section says; where it says nothing, this is the default.

1. **Ask one question** about what I already know about it, and wait.
2. **Research before planning.** Read current official documentation and good primary sources online, and look at how
   the concept shows up in the code I'm working on, so the curriculum fits my situation. Never teach from memory
   alone.
3. **Show the curriculum** up front: a short numbered list of lessons. Lesson 1 always motivates the concept: the
   problem we have, what we want, and how this concept solves it. Order the rest so each idea follows naturally from
   the one before (scaffolding): intuition first, then the details.
4. **Teach it as a dialogue**, one lesson at a time:
   - Pace each message by my message length (my profile; about 500 words if it says nothing), ending in a pause: a
     check question, or "ready for the next step?". Split a long lesson across messages; never squeeze it.
   - Signpost every message: where we are ("Lesson 2 of 5: …"), what we've understood so far, and what comes next.
   - Walk through any process step by step, like a debugger: show how the inputs and outputs change at each step,
     with the big picture kept in view.
   - Code snippets throughout: one or two simple textbook examples first, then an example from my code.
   - When I'm stuck, explain differently rather than repeating yourself; go back a lesson if needed.
5. **When the curriculum is done**, or I say I understand, give a short recap and ask whether I'd like a note, unless
   my profile says not to save notes.
6. **The note**, if I want one: `<concept-in-kebab-case>.md` in the notes folder my profile names, one note per concept
   (update it if it exists). Plain Markdown, starting with this front matter:
   ```
   ---
   made-by: LETS /lets:learn
   date: <today, YYYY-MM-DD>
   ---
   ```
   - straight under `# <Concept>`, a short paragraph saying what it is and why it exists;
   - the topic's main ideas, in the curriculum's order, with code snippets;
   - extra emphasis on the parts I struggled with, and how they finally made sense;
   - common pitfalls, the sources used, and one line of context (date, repo, what I was building).
   Keep secrets, credentials, internal hostnames and personal data out of it. If the notes folder is in a git repo,
   never run git there (I commit it myself), and if this repo's `lets.kind` isn't `own`, leave its name out and turn
   examples from its code into made-up ones that teach the same thing.
7. Finish with the note's path (if any) and: "Return to your main session with `/resume`."
