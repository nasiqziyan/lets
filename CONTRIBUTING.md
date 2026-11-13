# Contributing

Issues are welcome: bugs, a guard rule that's wrong, a command that confused you. For a pull request, open an issue
first and agree the change there; changes to the guard and hooks get an extra review (`CODEOWNERS`).

Working on LETS itself:

```bash
npm install                      # OpenSpec, for the tests
scripts/check.sh                 # lint, types, unit tests, the plugin build, end-to-end tests (needs uv)
python3 scripts/maint.py build   # after changing skills/, notes/, plugin.map or renames.json
```

Vendored skills (`vendor/`) are never edited by hand: `scripts/maint.py intake` takes upstream changes, and LETS's
words are applied by `renames.json` at build time.
