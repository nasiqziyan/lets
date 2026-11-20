---
name: change-close
description: "Close a change once its pull request is approved and before it merges (its deltas go into the living specs, and it is archived), or drop a change you have decided not to do."
argument-hint: "<change> [--drop]"
disable-model-invocation: true
---

1. The change is the argument; if there's none, the one `~/lets/bin/lets note` records for this branch; else propose
   one and wait.
2. **Shipped or dropped?** With `--drop`, it's dropped (step 5). Otherwise, if every task in `tasks.md` is ticked and
   I've told you the pull request is approved (ask if I haven't, and wait), it's shipped (step 3). If tasks are
   unticked, list them and ask: **Keep it open** (default: stop here, nothing changes) or **Drop it**.
3. **Shipped.** From the planning root: `openspec validate <change> --strict`, then `openspec archive <change> -y`.
   Show what it changed in the specs. In each spec it created, replace OpenSpec's "TBD" Purpose with one sentence from
   the proposal.
4. Where the files go:
   - **Separate planning repo**: commit there as the guide says. Nothing in the code repo changes; tell me I can merge.
   - **Plans in this repo**: the spec updates and the archived folder go on the change's branch. Draft that commit's
     message ("Close <change>: specs updated"); I commit and push it, then merge.
5. **Dropped.** Ask for one line of why (I may have given it). Add `## Dropped` with that line to the end of
   `proposal.md`, then `openspec archive <change> -y --skip-specs`: the specs don't change. If its epic's map lists it
   under `## Changes`, mark it there as dropped. Commit as the guide says (plans in this repo: draft the message).
6. If the change has an issue (`x-lets-issue` in its `.openspec.yaml`), close it: shipped, or "Not doing this: <why>".
   Close it where it was made, as the guide's "Issues" says (the code repo's issues, or a private planning repo's own
   project); if `gh` or `glab` doesn't work there, tell me to close it.
7. Shipped: when my profile allows suggestions, suggest `/lets:retro <change>`.
