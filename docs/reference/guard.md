# The guard

The guard checks every shell command and file edit an agent makes, in Claude Code and Codex, before it runs. It binds
agents only: you stay free to do anything yourself. It takes about 55 ms a call and uses no tokens unless it blocks.

## What it blocks

| Rule | Examples |
|---|---|
| Bypassing or changing the gates | `git commit --no-verify`, `HUSKY=0`, `git -c core.hooksPath=…`, writing `lets.*` settings, editing `.git/` or git's config files, `lets` commands that are yours (`walkthrough complete`, `setup`, `install`, `profile <question>`, `update`, `uninstall`, `doctor --yes`) |
| Throwing away uncommitted work | `git reset --hard`, `git checkout .`, `git clean -fd`, `git stash drop`, `git branch -D` |
| Weakening a gate, as the edit is made | a new skipped or focused test, an unexplained `noqa` or `eslint-disable`, a lowered coverage threshold, a deleted assertion |
| Going further with git than `lets.agents` allows | `local` (default): no commits or pushes. `commit`: commits to feature branches, after the floor check and the quick check. `ship`: also pushes a feature branch and opens a PR, once a walkthrough is recorded |
| A person's job | merging or approving a PR, `--admin`, pushing to a shared branch |
| AI mentions | an AI in a branch name, commit message, or PR title or description; co-author trailers; in every repo. If you chose an AI credit, its trailer (and pull request note) is required instead, and nothing else may mention an AI |
| Where plans are private | any `gh` or `glab`; committing the owners' docs, agent config or planning files |

## When a block is wrong

A block message says why. For a weakened gate that's right on this branch, it prints the exact command that approves
it (`git config --add branch.<name>.letsAllow '<finding>'`), which only you can run.

## When the guard can't run

Without Python 3.11+, or if the guard itself fails, `git`, `gh` and `glab` commands are blocked (so nothing is
committed, pushed or opened unchecked) and the session-start check tells you. Run `lets doctor`.

It's a tripwire, not a sandbox: it reads commands as text. CI, protected branches and a human reviewer stay the final
gates.
