# Work with a team

## The team uses LETS

Choose where plans live when you run `lets setup`:

- **In this repo**: plans go in `plans/`, committed with the code and reviewed in pull requests like any other file.
  `plans/README.md` explains the folder to teammates who don't use LETS. A change's plan travels on its branch, so it
  arrives in the change's pull request.
- **In a planning repo for the team**: plans live in a separate repo everyone clones. LETS commits there locally after
  each command; people push when they choose. Building commands run `lets sync` first (fast-forward only) so you plan
  on the team's latest files.

Teammates join by running `lets setup` in the same repo: it recognises plans already in the repo, or asks for the
planning repo's clone URL.

## The team doesn't use LETS

Choose **In a private planning repo**. Nothing agent-related reaches the team's repo or its forge: no planning files,
no agent config, no `gh` or `glab`. The guard enforces it. Your plans live in a private repo of your own.

If the team later adopts LETS, re-run `lets setup` and choose a new home: see [Move plans](move-plans.md).

## Issues

Optional: see [Track changes as issues](issues.md).
