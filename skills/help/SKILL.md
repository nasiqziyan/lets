---
name: help
description: Answer my question about LETS itself (setting it up, its settings, its commands, additions, the guard) from LETS's own docs, with the exact command to run. It changes nothing.
argument-hint: "[question about LETS]"
---

Answer questions about using LETS, not about my code or my plans. For "what should I do next" or "which command for
this work", that's `/lets:next`: say so in one line and stop.

1. **No question:** list what you can answer about, one line each: installing and updating, setting up a repo and
   where its plans live, the profile and settings, the commands, additions (`/lets:add`), the guard, and
   troubleshooting. Then ask what I'd like to know.
2. **With a question:** first run `~/lets/bin/lets where` (this repo's choices, so the answer fits here), then read
   the docs that cover it, under `~/lets/docs/`: `how-to/README.md` and `reference/README.md` list the pages,
   `troubleshooting.md` covers errors. `~/lets/bin/lets --help` and `~/lets/bin/lets <command> --help` give the
   terminal commands. Answer only from what they say; if they don't cover it, say so rather than guess.
3. **The answer:** a few sentences, the exact command to run (a terminal command for me to run, or a `/lets:`
   command to type), and the doc page it came from (its path under `~/lets/docs/`).
4. Change nothing: no settings, files or commands run beyond the reads above. When the answer is a terminal command,
   I run it.
