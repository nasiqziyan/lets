# Work with a team

`lets setup` asks two separate questions about a team's repo.

## Has the team agreed to agents working in it?

- **Yes** (your own repo, or the team has agreed): agents may work with the team's AI instructions (`CLAUDE.md`,
  `AGENTS.md`, `.claude/`), its own docs in the repo, and its GitLab or GitHub (`glab`, `gh`), as far as the git
  setting you choose allows.
- **No**: agents leave the team's way of working alone: its AI instructions, its own docs in the repo (glossary, ADRs,
  coding standards) and its GitLab or GitHub. Nothing agent-related is committed there, and the guard enforces it.
  Agents still help you write code; you commit and push it as usual. Agents can't open merge requests, so the git
  setting stops at Commit.

## Where do the plans live?

- **In this repo** (only where the team has agreed): plans go in `plans/`, committed with the code and reviewed in
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

If the team's answer changes later, re-run `lets setup`. To move plans to a new home, see [Move plans](move-plans.md).

## Issues

Optional: see [Track changes as issues](issues.md).
