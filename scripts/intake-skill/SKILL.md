---
name: intake
description: Monthly upstream intake. Report what changed in the sources this fork vendors, run each change through the fit test, and apply only what I approve.
disable-model-invocation: true
---

Run this from the root of `~/lets`. Nothing changes until I've decided, item by item.

1. Run `bin/lets intake report`. It fetches every upstream in `UPSTREAM.lock`, compares the pinned commit with the newest one, and writes `intake/<date>.md`. Read that file.
2. Group the changes: each vendored skill or reference that changed, new skills or files upstream, anything removed or renamed, and new tool versions (OpenSpec). For each group, write one line saying what changed and why upstream changed it (quote the changelog when there is one).
3. Put each group through the fit test. Answer every question in a few words:
   1. Does it fix a failure I've seen, or a bug upstream documented? (A hypothetical improvement doesn't count.)
   2. Does it duplicate a job something in this fork already owns?
   3. Does it contradict a choice in `AGENTS.md` (explicit commands only, the change as the unit, git kept local, nothing agent-related in repos where LETS isn't welcome, order of truth)?
   4. Who invokes it, and what does it cost? Model-invoked skills add to every session's skill list (helpers in `plugin.map`); verbs and specialist skills only add their name; the report shows the change in characters.
   5. Does it work in both Claude Code and Codex?
   6. Does it rename or move a command, file or folder I rely on? What would break?
   7. Does it add scripts, network calls or new permissions? Read them.
   8. Can a case in `evals/` show that it helps?
   9. Does it make something already in the fork unnecessary?
4. Recommend ADOPT, DEFER or REJECT for each group, with the deciding reason. Show them as a table and ask me to decide, a few rows at a time. Wait for my answers.
5. Apply only what I approved: `bin/lets intake apply <upstream> <commit> [--paths <path> ...]`. For a new skill, add it to `plugin.map` and run `bin/lets build`. For a new source I approved, use `bin/lets intake add`.
   - If `bin/lets build` stops because a phrase in `renames.json` no longer appears, show me the new upstream wording and propose the updated rename row; change nothing else in the vendored text.
   - OpenSpec: LETS drives its command-line tool directly. Move the pinned version only after `tests/run.sh` has run the real OpenSpec commands (create, validate, close) on the new version and passed; otherwise recommend DEFER.
6. Run `bin/lets doctor` and `tests/run.sh`, and fix anything they report. If a skill the daily flow uses changed, or my default model changed since the last intake, run the behaviour evals (README, Upkeep) and note the pass rates in the report. Add one line per decision to `UPSTREAM.md`: date, upstream, from and to commit, the decision and its reason (rejections too, so they aren't re-proposed next month).
7. Create a branch named `intake/<date>` and leave the changes for me to commit (`/lets:commit-message` drafts the message).
