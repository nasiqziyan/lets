# Make a small fix without planning

`/lets:patch` is for work that changes no behaviour: a typo, a small refactor, config, a dependency bump, or a bug fix
that makes the code do what its spec already says. It has no plan in `plans/`: the commit and the pull request are
its record.

```text
/lets:patch the footer says "Copyrite"
```

The agent checks it really is a patch. If the work would change behaviour, add something, or touch a decision, it
stops and suggests `/lets:change-start` instead. Otherwise it proposes a branch, does the fix (pair or agent mode, as
the repo is set up), shows the evidence that it works, and drafts the commit message. `/lets:review` works on a patch
branch too.

If a patch grows, or several pile up on one branch, the agent suggests moving the work into a change.
