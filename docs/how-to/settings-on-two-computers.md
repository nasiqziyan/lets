# Use the same settings on two computers

Your LETS settings are one folder: `~/.config/lets/` (your profile, `config.json`, and your additions). Everything
else LETS keeps is for one computer only (backups and logs in `~/.local/state/lets/`), and paths in the settings are
stored as `~/...`, so the folder works on any computer.

## With git (no other tools)

On the first computer, once, with an empty private repo made on GitHub or GitLab:

```bash
cd ~/.config/lets
git init && git add -A && git commit -m "My LETS settings"
git remote add origin git@github.com:you/lets-settings.git
git push -u origin main
```

On the second computer, once:

```bash
npm install -g @nasiq/lets
git clone git@github.com:you/lets-settings.git ~/.config/lets
lets install              # finds your profile and asks nothing
```

After a change (`lets profile length`, a new addition): `git add -A && git commit -m … && git push` on one, and
`git pull` on the other. Then run `lets profile` once there so Codex gets the new copy.

## With chezmoi

If you keep your other settings ("dotfiles") with [chezmoi](https://www.chezmoi.io/), add the folder like any other:

```bash
chezmoi add ~/.config/lets
```

New files (a new addition, say) need `chezmoi add ~/.config/lets` again; changes to existing ones need
`chezmoi re-add`. With `autoCommit` and `autoPush` set in chezmoi's config, both commit and push for you. On another
computer, `chezmoi init --apply <your repo>` puts everything in place; `chezmoi update` brings later changes.

To keep some files on one kind of computer only, chezmoi asks each computer once (`promptBoolOnce` in
`.chezmoi.toml.tmpl`) and skips files by the answer (`.chezmoiignore`). LETS's settings are the same everywhere, so
they need none of that.
