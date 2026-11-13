---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
user-invocable: false
---

> **LETS:** you're running inside a LETS command; its instructions win where they differ from this text. Planning files (notes, research, glossary, ADRs, epics, questionnaires) go in the planning root that `~/lets/bin/lets where` prints, never in a branch or tracker of their own, and `~/lets/guides/planning.md` says how. Where this text says to commit, push, open a PR or post to an issue or tracker, do that only as the guide and `git config --get lets.agents` allow; otherwise leave it for me and say what to do. Where it says `/setup-matt-pocock-skills`, that's `lets setup`, which I run in a terminal. No branch name, commit message or pull request text you write mentions an AI, in any repo. Below is the skill as its author wrote it, in LETS's words.

Spin up a **background agent** to do the research, so you keep working while it reads.

Its job:

1. Investigate the question against **primary sources** (official docs, source code, specs, first-party APIs), not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Write the findings to a single Markdown file, citing each claim's source.
3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.
