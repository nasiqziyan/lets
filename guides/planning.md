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

When `home` is a planning repo for the team, run `~/lets/bin/lets sync` first, so you plan on the team's latest
files. If it can't fast-forward, stop and tell me.

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

Optional, offered at the end of `/lets:epic-split` and `/lets:change-start`, only where the plans are shared with the
team (`lets.kind own`) and `gh` or `glab` works here. Issues point at the plans; they never copy them.
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

- **Separate planning repo**: after a command writes planning files, commit them in the planning repo with a message
  naming the command and what changed (`epic-resolve: 03 One realm or two?`). Never push: I push when I choose.
- **This repo**: planning files are ordinary repo files. Leave them uncommitted and tell me which ones changed. A
  change's folder belongs on the change's branch, so it arrives in the change's pull request.
