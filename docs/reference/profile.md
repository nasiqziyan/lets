# The profile

How you like to work, asked at `lets install` and loaded into every session. Change an answer with
`lets profile <question>`.

| Question | Answers (default first) |
|---|---|
| `build` | `pair`: you write the code, the agent guides and checks it · `agent`: the agent writes it, then walks you through |
| `tests` | `propose` per task · `always` · `ask`: only when you ask |
| `git` | `local` · `commit` · `ship` |
| `ai-credit` | never · a trailer in each commit · a trailer and a pull request note (`Made with AI assistance.`). Trailers: `Assisted-by: Claude Code`, `Co-authored-by: Claude <noreply@anthropic.com>`, `Generated-by: Claude Code`, or your own. Branch names never mention an AI. |
| `questions` | one decision at a time · in rounds (a numbered batch, each with a recommended answer; "yes" accepts them all) |
| `suggestions` | yes: learning detours and retros · no |
| `notes` | where `/lets:learn` saves notes: LETS's folder (`~/.local/share/lets/learning/`) · a folder of yours · none. Changing it moves the notes already saved, after you agree. In a folder inside a git repo, LETS never commits: the guard stops agents running git there. |
| `length` | Medium, about 500 words · Short, about 250 · as long as it needs · your own number. Long explanations are split across messages, never shortened to fit. |
| `updates` | yes, at most once a day · no |
| `explaining`, `teaching`, `code-style` | LETS's default text, or your own (edit the profile file) |

`build`, `tests`, `git` and `ai-credit` are defaults for new repos; each repo keeps its own choice (`lets setup` changes it).
