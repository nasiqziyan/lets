---
name: lens
description: Look at the code through one lens (architecture, security, performance, api, frontend and the rest) and report what it finds. A lens never changes code.
argument-hint: "[lens] [what to look at]"
---

A lens reports and advises; it never changes code.

1. **Which lens.** The argument's first word, or a unique prefix of it (`perf` → performance). With none, list them
   with one line each and ask which:

   | Lens | Looks at |
   |---|---|
   | architecture | shallow modules and leaky seams: where the design could deepen |
   | api | interfaces and contracts: naming, errors, versioning |
   | browser | the running page in a browser: console, network, layout |
   | ci | the pipeline: speed, reliability, what it checks |
   | constraints | the rules the system must keep, written down and checked |
   | frontend | components, state, accessibility |
   | launch | readiness to ship: rollout, monitoring, rollback |
   | migrate | deprecations and migrations: moving users off the old way |
   | observability | logs, metrics and traces that answer real questions |
   | performance | where time and memory go, measured |
   | security | trust boundaries, secrets, injection, auth |
   | simplify | code harder to read than it needs to be |

2. Read `~/lets/plugin/refs/<lens>/SKILL.md` and follow it for what I pointed at (the whole repo if nothing).
3. Report: one table of findings (finding, where, why it matters, what to do), most important first. Verify each
   against the code; drop what doesn't hold up. Save it as `research/<lens>-<YYYY-MM-DD>.md` in the planning root,
   and commit as the guide says.
4. End with the next step for the finding I pick: `/lets:patch` if it changes no behaviour, `/lets:change-start
   <name>` for one pull request, `/lets:epic-start <name>` for more, or `/lets:change-revise <change>` if it belongs
   to a change that's still open.
