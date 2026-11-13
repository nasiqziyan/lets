# Plan across several repos

When separate repos make one product (an `api` and a `web`, say), they can share one planning repo.

```bash
cd ~/code/shop            # the folder that holds the repos
lets setup                # choose "Several related repos", tick the repos, then a planning repo for the team
```

The planning repo is cloned next to the repos. In the folder itself, `lets where` says it's a group folder: plan epics
there with `/lets:epic-start`. Each change is one pull request in one repo, so work that spans repos is split into one
change per repo, and each change records its repo. Build each change inside its own repo.

A repo added to the folder later is offered the group's planning repo when you run `lets setup` in it.
