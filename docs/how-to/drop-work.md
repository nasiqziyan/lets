# Stop a change or an epic

Most changes ship, so `/lets:change-close` assumes that: with every task ticked, it closes the change as shipped
without asking (with a planning repo, LETS does this by itself once the pull request is merged).

When tasks are still open, it asks: **Keep it open** (the default) or **Drop it**. To drop straight away:

```text
/lets:change-close try-a-thing --drop
```

It asks for one line of why, records it at the end of the proposal, and archives the change without touching the
specs. To stop a whole epic: `/lets:epic-revise <epic> --drop`.
