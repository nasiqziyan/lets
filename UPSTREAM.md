# Upstream ledger

What this fork takes from whom, and every intake decision. `UPSTREAM.lock` holds the exact commits and file checksums; `bin/lets doctor` fails if a vendored file is edited by hand.

## Sources

| Source | Pinned | Taken | Mode |
|---|---|---|---|
| [mattpocock/skills](https://github.com/mattpocock/skills) (MIT) | 1.3.1 @ `59db609` | 24 skills: 10 as helpers in the plugin under their own names (his skills call them by name), the rest read by LETS verbs from `vendor/` | verbatim |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT) | 0.6.13 @ `aeac41d` | 18 skills (17 as typed `/lets:` commands under short names, `doubt` also part of `/lets:check`; code-review-and-quality read by `/lets:check`) and 5 reference checklists | verbatim; a LETS note goes above the text in the built copy, never into the vendored file |
| [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) (MIT) | `@fission-ai/openspec` 1.15.0 | the CLI and its stock `spec-driven` schema, configured through `openspec/config.yaml` | tool; installed per repo by `lets setup --specs` |

LETS's own: `skills/` (the verbs), `notes/`, `plugin.map`, `AGENTS.md`, `openspec/config.yaml`, `references/`, `lib/`, `agent-hooks/`, `ci/`, `evals/`, `tests/`. `plugin/` is built from these and the vendored files by `lets build`.

## Deliberately not taken (so intake doesn't re-propose them without new evidence)

- Addy's `interview-me` (collides with grilling), `test-driven-development` (puts refactoring inside the loop where Matt's `tdd` puts it in review: two TDD owners contradict), `spec-driven-development` and `planning-and-task-breakdown` (OpenSpec and to-spec/to-tickets own specs and tickets), `incremental-implementation` (`/lets:build` owns building), `debugging-and-error-recovery` (Matt's `diagnosing-bugs` owns it; Tessl scored it 97) and `using-agent-skills` (a second router; `/lets:next` routes).
- Matt's `implement` (replaced by `/lets:build`, which pairs and keeps git local), `ask-matt` (replaced by `/lets:next` and `/lets:help`) and `grill-me` (`/lets:align` covers it).
- Addy's 9 commands and personas, and Superpowers' session-start bootstrap: a second command set and router on top of LETS's.
- A forked OpenSpec schema: the stock schema plus `config.yaml` rules reaches the agent the same way and needs no porting at each OpenSpec release.
- Matt's `misc/` and `in-progress/` skills: frozen or unfinished upstream. `misc/git-guardrails-claude-code`'s idea (block commands that discard work) is covered by the guard, in both harnesses.
- Addy's `testing-patterns.md`: overlaps Matt's `tdd/tests.md` and `tdd/mocking.md`.
- Vendoring with `git subtree`: it would pull every upstream folder into the fork and lose the per-file checksums and the risky-line read in the intake report.
- Git hooks as gates: hook managers fight over `core.hooksPath`, and gates bind agents, not you. Your own commits get warning hooks only, and only where no hook manager owns the hooks.
- A Claude Code output style for pairing: Codex has no equivalent, so one protocol file serves both.

## Decisions

| Date | Source | From → to | Decision | Reason |
|---|---|---|---|---|
| 2026-10-27 | all | initial | adopted as above | round-3 research and two independent red teams |
| 2026-10-27 | mattpocock/skills | 1.3.1 | `teach` unlinked | writes into work repos; `/detour` covers it |
| 2026-10-27 | (fork) | v6 | floor guard frozen | third review: each added rule widens the surface; new patterns go to per-repo linters via `/retro` |
| 2026-10-27 | (fork) | v10 | floor guard split: block new markers, ask about the rest | sixth review: on unseen diffs v9 blocked 8% of routine changes (all test consolidations) and missed 63% of weakening variants. Blocking stays frozen and narrow; the judgement calls moved to the walkthrough, where a false flag costs a question |
| 2026-10-28 | (fork) | v13 | renamed LETS; one plugin (`/lets:<verb>` in Claude Code, `$lets:<verb>` in Codex) | his choice of name. Tested on Claude Code 2.1.312 and Codex 0.164.0: a plugin in `~/.claude/skills/lets` loads live as `lets@skills-dir`; Codex installs it from the fork's marketplace and lists `lets:<name>`; a bare-name Skill call (`grilling`) still resolves inside the plugin (3 of 3 runs) |
| 2026-10-28 | addyosmani/agent-skills | 0.6.13 | 18 skills taken, all typed-only | he wants breadth; typed-only skills add only their name to the listing, which was the budget objection. The overlap research recommended which 7 to leave out |
| 2026-10-28 | mattpocock/skills | 1.3.1 | `teach` taken as `/lets:study`, in a folder of its own | it writes into the current directory, so `/lets:study` stops in a code repo and suggests `~/lets/learning/topics/<topic>/` |
| 2026-10-28 | (fork) | v13 | git stays local by default; repos are yours or not; edits checked as they're made | his answers: he commits and pushes; nothing agent-related reaches a remote that isn't his. The blocking floor-guard findings now stop the edit itself |
| 2026-10-28 | (fork) | v13 | ask about changed assertions and relaxed CONSTRAINTS.md rules | compared with Addy's floor guard on 593 cases: his alone caught weakened assertions. Costs 4 extra questions on 573 realistic diffs and 4 on 195 cases; catches 8 of the 22 recorded misses |
| 2026-10-28 | (fork) | v13 | the tenth (cold) review: vendored helpers get a LETS note too; outputs that could leak are redirected to `.lets/`; learning notes kept out of the fork's git; one review owner | its must-fix findings: wayfinder, prototype and wizard told agents to commit or push; questionnaires, research and ADR folders could reach a team remote; notes mirroring work code sat in a tracked folder |
| 2026-10-28 | (fork) | v13 | OpenSpec's skills hidden through `skillOverrides` | verified live on Claude Code 2.1.312: with the setting the model is offered none of the six OpenSpec skills, without it all six |
| 2026-10-28 | (fork) | v13 | the ninth (blind) check's 409 guard cases kept as a test | 4 false blocks fixed (moving a skipped test between files, `--help`); leaks fixed: `eval`, `$(...)`, pipes into a shell, `xargs`, git aliases, `python -c`, `commit-tree`, commits on a shared branch, agent-config edits in repos that aren't mine, approvals that covered every identical marker. Renamed or moved skips become walkthrough questions |
