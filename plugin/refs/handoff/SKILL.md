---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
disable-model-invocation: true
---

> **LETS:** you're running inside a LETS command; its instructions win where they differ from this text. Planning files (notes, research, glossary, ADRs, epics, questionnaires) go in the planning root that `~/lets/bin/lets where` prints, never in a branch or tracker of their own, and `~/lets/guides/planning.md` says how. Where this text says to commit, push, open a PR or post to an issue or tracker, do that only as the guide and `git config --get lets.agents` allow; otherwise leave it for me and say what to do. Where it says `/setup-matt-pocock-skills`, that's `lets setup`, which I run in a terminal. No branch name, commit message or pull request text you write mentions an AI, in any repo. Below is the skill as its author wrote it, in LETS's words.

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS (`$TMPDIR`, else `/tmp`; `%TEMP%` on Windows) - not the current workspace.

Include a "suggested skills" section in the document, naming which skills the next agent should call the Skill tool for.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
