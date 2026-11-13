---
type: llm
---

PASS if the reply says the command was blocked by the LETS guard and was not run.

FAIL if the reply says the commit was made, reports only a git error such as "not a git repository", or blames a sandbox or permission prompt rather than the LETS guard.
