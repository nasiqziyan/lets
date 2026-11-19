# The planning root (read by every planning command)

## Find it first

Run `~/lets/bin/lets where` before reading or writing any planning file. In a code repo it prints:

```text
planning root: /home/me/plans/shop-plans   # where every planning file below lives
code repo:     /home/me/shop/api (api)      # where code edits go, and this repo's name
group:         api, web                     # only when several repos share the plans
home:          a planning repo for the team # or: plans in this repo, or a private planning repo
build:         pair · test-first: propose · git: local   # this repo's choices; they override my profile's
check:         npm run -s check             # the repo's quick check, if it has one
additions:     ~/.config/lets/additions/build.md   # steps added to LETS commands (mine, then the team's)
```

With plans in this repo, the planning root is its `plans/` folder.

In a folder that holds several repos sharing one planning repo (a group folder), it prints the planning root, the
code repos and `home: a group folder`: plan from there, but build each change inside its own repo.

If it says the repo isn't set up, stop and tell me to run `lets setup`. Paths below are relative to the planning root.
Code is read and edited in the code repo; planning files are written under the planning root. With plans in this repo
they are the same folder.

When the plans are in a separate planning repo with a remote (a team or a private one), run `~/lets/bin/lets sync`
first, so you plan on the latest files: the team's, or mine from another computer. If it can't fast-forward, stop and
tell me.

## Layout

```text
openspec/specs/              living specs: how the system behaves now
openspec/changes/<change>/   open changes; closed ones move to openspec/changes/archive/
epics/<epic>/map.md          an epic's map (its `## Changes` list, once split, in delivery order)
epics/<epic>/prerequisites/  one file per prerequisite
epics/<epic>/overview.md     the epic explained for readers
epics/<epic>/inputs/         source material for the epic (read only)
research/<topic>.md          research findings
docs/adr/                    decisions worth recording (ADRs)
questionnaires/              questions for someone else
GLOSSARY.md, CODING_STANDARDS.md, CONSTRAINTS.md
additions/<command>.md       the team's own steps added to a LETS command (mine are in ~/.config/lets/additions/)
```

Create files and folders lazily, when there's something to write. With a separate planning repo, also read the code
repo's own `GLOSSARY.md`, `docs/adr/` and `CODING_STANDARDS.md` if they exist, but never edit them: mine go in the
planning root.

## Words

epic (too big for one pull request), map, prerequisite (types: research, grilling, prototype, action; one "waits on"
another), decision, ADR, overview, change (one pull request), task (one vertical slice of a change, built in one
session), delta (a change's spec changes), spec (OpenSpec's living specs). Use these words in every file and message.
Helpers (grilling, domain-modeling, research, prototype, tdd and the rest) are named bare, never as `/lets:` commands:
only the commands in `/lets:next` are typed.

## Short forms

Every command that takes an epic, change, prerequisite, task or lens accepts a short form. A unique prefix is enough
(`shop` for `shop-checkout`, `9` or `09` for prerequisite `09`). If several match, list them and ask which; if none
match, list what exists. Say which one you took ("Taking take-card-payment.") before starting.

## Names

- **Changes**: short, starting with a verb, saying what the work does: `add-catalogue`, `take-card-payment`,
  `add-staff-admin`. No epic name and no number in it: a change that belongs to an epic says so with
  `x-lets-epic: <epic>` in its `.openspec.yaml`, and the epic's map orders its changes.
- **Branches** are mine to name. Building commands record which change or patch a branch is for with
  `~/lets/bin/lets note change <change>` (or `note patch <name>`), and `lets note` reads it back. With no note, a
  branch whose name contains exactly one open change's name is for that change.

## Epic files (the tracker for wayfinding)

Where Matt's wayfinder text talks about the issue tracker, the map issue and child issues, these files are the
tracker:

- **Map**: `epics/<epic>/map.md`, with the sections Destination, Notes, Decisions so far, Not yet specified, Out of
  scope.
- **Prerequisite**: `epics/<epic>/prerequisites/NN-<slug>.md`, numbered from `01`:

  ```markdown
  # 03: One realm or two?
  Type: grilling
  Status: open
  Waits on: 01

  ## Question
  <the decision or investigation this resolves>
  ```

  `Type` is research, grilling, prototype or action. `Status` is open, claimed or resolved. `Waits on` lists
  numbers, or `none`.
- **Ready** (the frontier): open, unclaimed prerequisites whose `Waits on` are all resolved; first by number.
- **Claim**: set `Status: claimed` and save, before any work.
- **Resolve**: append `## Answer`, set `Status: resolved`, then add one line to the map's Decisions so far: the
  prerequisite's title as a link to its file, and a one-line gist.
- **Research findings** go in `research/<topic>.md`, linked from the prerequisite's answer. No branches, no pushes.
- **Out of scope**: set `Status: resolved`, answer "out of scope: <why>", and add a line to the map's Out of scope.

## Research in the background

A research prerequisite needs nothing from me, so it runs while I do something else.
- Claim it, then start one background agent for it (one per prerequisite). Tell the agent the question, what to
  read, to write its findings to `research/<topic>.md` and nowhere else, to make no commits, and to report a short
  summary. Without background agents (Codex, for one), leave it open and ready instead.
- The session that started an agent records its result when it reports, one result at a time: re-read the
  prerequisite and the map, write the answer, resolve it, and commit those files and the research file.
- Keep talking with me meanwhile; research never waits for me, and I never wait for it.

## Ending a step

Every epic step ends the same way, so I always know the next move:
- What changed, in a line or two, then **Ready now**: number, title and type of each ready prerequisite, with one
  recommended.
- The next move, in these words: "Start a fresh session (`/clear` or a new tab), then run `<command>`." Each step
  reads what it needs from these files, so a fresh session loses nothing. Never offer to carry on here ("Shall I
  take 01?").
- Ready research prerequisites that nothing is running: say they need nothing from me and can run in another tab at
  the same time, with `/lets:epic-resolve <epic> research`.
- Research agents this session started that are still running: name them, and say "You don't need to wait: start
  the next step in a new tab. Leave this tab open: it records their answers as they finish, then says it's done."
  Then stay until the last one is recorded and committed, and finish with "All research recorded; this tab is
  done." and Ready now again if it changed.

## Two sessions at once

I may work on one prerequisite while research for another finishes in a second session.
- Re-read the map and a prerequisite just before editing them, and change only your own lines.
- Commit only the files you changed (`git add <paths>`, never `git add -A`). If git says the index is locked, wait a
  moment and try again.
- A claimed prerequisite with no answer may belong to a session that was closed. Say so: if its research file
  exists, offer to record it now; if not, offer to start its research again.

## Changes (OpenSpec)

Run OpenSpec's command-line tool from the planning root, never its own agent skills or `/opsx:*` commands:

```text
openspec list                                   # open changes
openspec list --specs                           # the living specs
openspec show <spec> --type spec                # read one spec in full
openspec new change <change>                    # create the folder
openspec instructions <artifact> --change <change>   # the format for proposal, specs, design or tasks
openspec validate <change> --strict             # must pass before a change is ready
openspec archive <change> -y                    # close: merge deltas into specs, archive the folder
```

A change folder holds:
- `proposal.md`: the goal and scope (why, what changes, which capabilities);
- `design.md`: the decisions that apply to it;
- `specs/<capability>/spec.md`: its deltas; every requirement has at least one scenario, which is its acceptance;
- `tasks.md`: its tasks. **Each numbered group is one task**: `## 2. Filter handling`, a vertical slice built in one
  session, with checkbox steps under it and a last step that says how it's verified. Task numbers are group numbers; a task's name is its
  heading in kebab-case (`## 2. Email status changes` is `email-status-changes`), and commands take either.

With a group (several code repos sharing the plans), each change is one pull request in one repo: its
`.openspec.yaml` names that repo with `x-lets-repo: <repo>` (the name `lets where` prints). OpenSpec ignores keys
starting `x-`, so these are LETS's own labels (`x-lets-repo`, `x-lets-epic`, `x-lets-issue`). Building commands
(`build`, `review`, `walkthrough`, `change-close`) check `x-lets-repo`: if `lets where` prints a different code repo,
stop and tell me to cd into the right one. Work that spans repos is split into one change per repo.

## Checking a change

After writing or revising a change, check that its parts agree, and report only the mismatches:
- every requirement and scenario in its deltas is delivered by a task, and every task serves a requirement (or is
  prefactoring, said so);
- nothing in `design.md` contradicts a task or a delta;
- nothing contradicts an ADR (say which, and ask: change the plan, or record a new ADR that supersedes it).

## Issues

Optional, offered at the end of `/lets:epic-split` and `/lets:change-start` where `gh` or `glab` works. Issues point
at the plans; they never copy them. Where they go:
- **Plans in this repo, or a team planning repo, and the team has agreed** (`lets.kind own`): the code repo's own
  issues.
- **A private planning repo**: the planning repo's own project, which only I see. Run `gh` or `glab` inside the
  planning root, never in the code repo.
- **A team planning repo where the team hasn't agreed**: don't offer issues.
- One issue per change (tasks stay in `tasks.md`), plus one for the epic. Title: the change's name in plain words
  ("Take card payment"). Body: a link to the change's folder and the command that builds it; for the epic, a link to
  its overview.
- **GitHub**: the epic's issue has the type Epic, and each change's issue is its sub-issue, blocked by the issues of
  the changes it waits on (`gh issue create --type Epic`, `--parent <n>`, `--blocked-by <n>`; gh 2.94 or newer).
- **GitLab Premium**: a GitLab epic, with each change's issue as a child, linked with "blocks". **GitLab Free**: a
  parent issue for the epic, each change's issue linked with "relates to" and a "Waits on #n" line.
- Record each change's issue number as `x-lets-issue: <n>` in its `.openspec.yaml`. LETS writes issues only when
  they're created and when `/lets:change-close` closes them.

A change with no behaviour change (a refactor, tooling) sets `skip_specs: true` in its `.openspec.yaml` instead of
inventing a delta. A bug fix that restores what a spec already says has no delta either.

## Commits

Commit messages, branch names and pull request text say what changed, never who or what wrote it: no AI mention or
trailer, in any repo, the planning repo included. If you'd rather credit AI help, choose a trailer (and a pull request
note) at install or with `lets profile ai-credit`; a repo can choose differently with `lets setup --ai-credit`. Branch
names never mention an AI.

- **Separate planning repo**: after a command writes planning files, commit the files it changed (not `git add
  -A`) in the planning repo with a message naming the command and what changed (`epic-resolve: 03 One realm or two?`). Never push: I push when I choose.
- **This repo**: planning files are ordinary repo files. Leave them uncommitted and tell me which ones changed. A
  change's folder belongs on the change's branch, so it arrives in the change's pull request.
