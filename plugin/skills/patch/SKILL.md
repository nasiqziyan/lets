---
name: patch
description: Make a small change that changes no behaviour (a typo, a small refactor, config, a dependency bump, a bug fix that restores what a spec says) without planning a change. Sends you to /lets:change-start when behaviour would change.
argument-hint: "<what to fix or tidy>"
disable-model-invocation: true
---

A patch changes no behaviour, so it has no plan: the commit and the pull request are its record. Like a semver patch
release: fixes and tidying, nothing new.

1. **Is it a patch?** It is when nothing a user or caller could notice changes, or it restores what a spec already
   says. If it would change behaviour, add something, or touch a decision, stop and suggest `/lets:change-start
   <name>`, saying why.
2. **The branch.** On a shared branch (`main`, `master`, `develop`, the default branch), propose a branch (a short
   name saying what it fixes; the name is mine to choose), create it when I agree, and record it:
   `~/lets/bin/lets note patch <name> --mode <pair|agent>` (the mode is this repo's build choice unless I said).
   On a feature branch, record the patch on it the same way.
3. **A bug:** call the Skill tool with "diagnosing-bugs" until we know the cause, and show me the evidence. If the
   fix needs a test, call the Skill tool with "tdd": a failing test that shows the bug first.
4. **Do it** in the mode recorded: pair mode (`~/lets/plugin/skills/build/pairing.md`) or agent mode.
5. **Evidence before done:** show the output that proves it (the tests, type check, build or linter it affects). Never
   claim done without it.
6. Draft the commit message as `/lets:build` does (what changed and why; no AI mention beyond the AI credit `lets where` shows). Then suggest `/lets:review`.
7. **Watch the size.** If it grows past a small diff, or behaviour starts to change, stop and suggest moving it into a
   change (`/lets:change-start`). When several patches pile up on one branch, suggest the same.
