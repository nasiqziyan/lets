# Security

## Reporting a problem

Please report security problems privately, through GitHub's **Report a vulnerability** button on this repository's
Security tab, not in a public issue. You'll get a reply within 14 days.

Most useful: what an agent (or a file, web page or comment it read) could make happen that the guard should have
stopped, the exact command or edit, and the output of `lets --version` and `lets doctor`.

## What LETS does and doesn't promise

- The guard is a tripwire, not a sandbox: it reads commands as text. CI, protected branches and a human reviewer stay
  the final gates.
- LETS never loosens Claude Code's or Codex's own permissions.
- LETS sends nothing about you anywhere. Its only network call is the update check (the npm registry's latest version
  number), which you can turn off.
- Releases are published from GitHub Actions with npm provenance, after a manual approval.

When working with code or content you don't trust, run your agent in a dev container or VM.
