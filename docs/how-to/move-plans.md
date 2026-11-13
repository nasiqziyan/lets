# Move plans to another home

Re-run `lets setup` in the repo and choose a different answer to "Where should the plans live?".

- **From a planning repo into the repo**: LETS copies the plans (not their history) into `plans/` on a new branch
  `lets-plans`, uncommitted. Review them, commit, and open a pull request. The old planning repo is left as it was.
- **From the repo into a planning repo**: the plans are copied in and committed there locally. The repo's `plans/`
  folder is left for you to remove in a pull request.

Open changes are asked about one by one: onto their own branch (when one exists; uncommitted, in a worktree of its
own), with the rest, or left behind to bring in later.

## When the new home already has plans

When a teammate already keeps plans there, every clash is asked about, with the difference shown and a default that
loses nothing:

| Clash | What you're offered |
|---|---|
| An epic or change with the same name | bring yours in as `<name>-2` (links updated), rename it, or skip it |
| ADR numbers | yours are renumbered after the highest there, shown side by side |
| A glossary term defined differently | keep theirs, use yours, or keep both (yours named after you) |
| `CODING_STANDARDS.md`, `CONSTRAINTS.md` | add yours below theirs under "From <you>'s plans", keep theirs, use yours, or see the difference |
| A spec | keep theirs and put yours beside it as `from-<you>.md`, keep theirs, use yours, or see the difference |
| Any other file | keep both, keep theirs, use yours, or see the difference |

A group's planning repo serves several repos, so its plans aren't moved into any one of them.
