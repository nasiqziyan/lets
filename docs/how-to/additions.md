# Add your own steps to a command

To change how a LETS command works for you without editing LETS (your edits would be lost on update), add an
**addition**: your own rule for one or more commands.

The easy way: describe the rule in your own words.

```
/lets:add every commit message should start with the ticket number, like ABC-123: Add order tracking
```

The agent works out which commands it affects (here `build` and `patch`, which draft commit messages), asks whether
it applies in every repo of yours or only to this repo's plans, shows the exact lines, and saves them only once you
agree.

Each addition is a Markdown file named after the command, which you can also write or edit yourself:

- Yours, in every repo: `~/.config/lets/additions/<command>.md`
- For one repo's plans, committed with them: `plans/additions/<command>.md` (or `additions/` in a planning repo).
  Everyone working on those plans follows it; in a private planning repo, that's only you.

```markdown
<!-- ~/.config/lets/additions/build.md -->
- Before showing the evidence, also run `make lint`.
- Use British spelling in commit messages.
```

The agent reads additions after the command's own steps; they win where they differ, except over the guard, which
they can't loosen. `lets where` lists the additions that apply in a repo, and updates never touch them.
