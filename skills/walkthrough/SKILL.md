---
name: walkthrough
description: Before the pull request, walk me through a change in the order the code runs and quiz me on it; then draft the pull request description. I record its completion myself.
argument-hint: "<change>"
---

The aim: I understand every line I ship, whoever typed it. Explain first, then check it landed.

1. The change is the argument; if there's none, the one `~/lets/bin/lets note` records for this branch; else propose
   one and wait. If `/lets:review` hasn't run since the last commit, suggest it first (I can skip it).
2. Run `~/lets/bin/lets walkthrough scope`. It prints the base commit, the committed files I haven't yet walked
   through, then `ask:` lines. If it reports uncommitted changes that belong to this work, stop: a walkthrough covers
   committed content only. If it prints no files, say so and go to step 7. Read `git diff <base> HEAD -- <those
   files>`, and the change's proposal and design for the why.
3. **Explain** the change in the order the code runs, not file by file: what each part does, why it's built this way
   (tie it to the change's decisions and tasks), and how the parts connect. Point at files and lines; skip mechanical
   edits. Ask whether I have questions, and answer them.
4. **Choose what to quiz:** at most five things that carry a decision or a risk (a behaviour change, an error path,
   concurrency, a data or API contract, security); one is enough for a one-line fix. Every `ask:` line is a change
   that loosens a check: quiz me on each of those too (what it loosens and why that's right here).
5. Ask them one at a time and wait for each answer, without hints. Then say what I got right and correct what I
   missed, pointing at the lines; if I couldn't answer, explain briefly and ask a follow-up I can now answer.
6. Finish with a table of the items, each "understood" or "gap". A gap: suggest a fix, or a detour (`/branch` or
   `/fork`, then `/lets:learn <concept>`), and stop there: don't tell me to record completion.
7. All understood: tell me to record it myself with `! ~/lets/bin/lets walkthrough complete` (in Codex, the same
   command in a terminal). Never run it yourself; the guard blocks you. Then draft the pull request description in a
   code block I can copy, with a title: follow `~/lets/plugin/refs/pr/SKILL.md` (what changes and why from the
   proposal, how it was tested from the tasks' verification, what a reviewer should look at first). With plans in this
   repo or a team planning repo, link the change folder (a planning repo's address comes from its remote). Write it the way the team writes theirs: no mention of AI or agents (except the
   pull request note `lets where` shows as the AI credit, if any), nothing that names a private planning repo. I push and open it, unless `lets.agents` is `ship` and I ask you to. After approval:
   `/lets:change-close <change>`, then I merge.
