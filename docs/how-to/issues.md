# Track changes as issues

Optional. At the end of `/lets:epic-split` and `/lets:change-start`, where `gh` or `glab` works, the agent offers to
create issues. Issues point at the plans; they never copy them. Where they go depends on the plans:

- **Plans in the repo, or a team planning repo, where the team has agreed to agents:** the code repo's own issues.
- **A private planning repo:** the planning repo's own GitLab or GitHub project, which only you see. Nothing is created
  in the team's repo.
- **A team planning repo where the team hasn't agreed:** issues aren't offered.

Wherever the plans live, agents can read the team's issues and merge requests (`glab issue view 42`, `gh pr diff`);
only writing to them needs the team's agreement.

- One issue per change (its tasks stay in `tasks.md`), plus one for an epic. The title is the change's name in plain
  words; the body links to the change's folder and gives the command that builds it.
- **GitHub**: the epic's issue has the type Epic; each change's issue is its sub-issue, blocked by the issues of the
  changes it waits on. Needs gh 2.94 or newer.
- **GitLab Premium**: a GitLab epic with each change's issue as a child, linked with "blocks".
- **GitLab Free**: a parent issue, each change's issue linked with "relates to", and a "Waits on #n" line.

`/lets:change-close` closes the change's issue (shipped, or "Not doing this: <why>" when dropped).
