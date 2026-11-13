# Track changes as issues

Optional. At the end of `/lets:epic-split` and `/lets:change-start`, where the plans are shared with the team and `gh`
or `glab` works, the agent offers to create issues. Issues point at the plans; they never copy them.

- One issue per change (its tasks stay in `tasks.md`), plus one for an epic. The title is the change's name in plain
  words; the body links to the change's folder and gives the command that builds it.
- **GitHub**: the epic's issue has the type Epic; each change's issue is its sub-issue, blocked by the issues of the
  changes it waits on. Needs gh 2.94 or newer.
- **GitLab Premium**: a GitLab epic with each change's issue as a child, linked with "blocks".
- **GitLab Free**: a parent issue, each change's issue linked with "relates to", and a "Waits on #n" line.

`/lets:change-close` closes the change's issue (shipped, or "Not doing this: <why>" when dropped).
