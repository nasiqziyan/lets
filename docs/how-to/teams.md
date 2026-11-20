# Work with a team

`lets setup` asks two separate questions about a repo.

## How should LETS work in it?

Both choices assume you're allowed to use AI agents on this code. Agents never merge, approve or push to a shared
branch, whichever you choose.

- **Individual use**: agents read the code, docs, issues and merge requests and help you write code, but change
  nothing the team sees: its AI instructions (`CLAUDE.md`, `AGENTS.md`, `.claude/`), its own docs in the repo
  (glossary, ADRs, coding standards) and its GitLab or GitHub. Nothing agent-related is committed there, and the
  guard enforces it. You commit and push as usual; agents can't open merge requests, so the git setting stops at
  Commit.
- **Full use** (your own repo, or the team has agreed): agents can also update its AI instructions, its own docs and
  its GitLab or GitHub (`glab`, `gh`), as far as the git setting you choose allows.

## Where do the plans live?

- **In this repo** (full use only): plans go in `plans/`, committed with the code and reviewed in
  pull requests like any other file. `plans/README.md` explains the folder to teammates who don't use LETS.
- **In a team planning repo**: a separate repo your teammates read and add to. Work can link to it: a pull request
  description can point at the change's plan.
- **In a private planning repo**: a separate repo only you see. Nothing links to it; agents never name it anywhere the
  team sees.

With a separate planning repo, LETS commits there locally after each command, and you push when you choose. Commands
run `lets sync` first (fast-forward only), so you plan on the latest files: your teammates', or yours from another
computer.

Teammates join by running `lets setup` in the same repo: it recognises plans already in the repo, or asks for the
planning repo's clone URL.

If the team's answer changes later, re-run `lets setup`.

## Several people on one epic

Claiming a prerequisite changes a file in your copy of the plans. Another session using the same folder sees the
claim straight away, but a teammate with their own clone doesn't until you push it and they pull. So two up-to-date
clones can both show the same prerequisite as open, and two people can start it.

When several people work on one epic, agree who takes what before starting, in chat or in the team's tracker: "I'll
take 03 (the payment provider research); you take 05 (the refund rules)". Then each claims their own. To move plans to a new home, see [Move plans](move-plans.md).

## Issues

Optional: see [Track changes as issues](issues.md).
