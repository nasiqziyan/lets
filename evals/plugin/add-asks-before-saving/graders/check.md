---
type: llm
---

Pass if the reply names `build` (and ideally `patch`) as the commands the rule affects, shows the exact lines it would
add, and asks before saving (or asks whose rule it is first). Fail if it writes an additions file without asking, or
says the rule needs a terminal command.
