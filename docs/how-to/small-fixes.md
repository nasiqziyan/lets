# Make a small fix without planning

`/lets:patch` is for small, clear work whose result can be checked: a typo, a small refactor, config, a dependency
bump, a bug fix, or a small visible edit such as renaming a button. It has no plan in `plans/`: the commit and the pull request are
its record.

```text
/lets:patch the footer says "Copyrite"
```

The agent checks it really is a patch. If the work raises a product or design decision, changes a promise users or
other software rely on (a published CSV column, an API field), or needs a living spec updated, it says which and
suggests `/lets:change-start` instead. Otherwise it proposes a branch, does the fix (pair or agent mode, as
the repo is set up), shows the evidence that it works, and drafts the commit message. `/lets:review` works on a patch
branch too.

If a patch grows, or several pile up on one branch, the agent suggests moving the work into a change.
