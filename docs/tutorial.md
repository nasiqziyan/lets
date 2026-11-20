# Tutorial: your first change

This takes about an hour. You'll plan one small piece of work in a repo of your own, build it in pair mode, review
it, and be walked through it, ending with a pull request you could open. Pick something small and real: a missing
validation, an empty state on a page, an export button. Something you'd finish in an afternoon by yourself.

You need LETS installed (`npm install -g @nasiq/lets`, then `lets install`; later, `lets update` updates it).

## 1. Set up the repo

In a terminal, in your repo:

```bash
lets setup
```

It asks three things. Choose **One repo**, then **In this repo** for where plans live (they go in a `plans/` folder,
committed with the code), then keep the defaults for how you build. It shows what it will change and asks before
making it. When it's done, `lets where` prints the result:

```text
planning root: /home/you/code/shop/plans
code repo:     /home/you/code/shop (shop)
home:          plans in this repo
build:         pair · test-first: propose · git: local
```

## 2. Plan the change

Open Claude Code in the repo and type:

```text
/lets:change-start add-order-export Shop owners want their orders as a CSV file
```

The agent asks you questions, one decision at a time, each with its recommended answer. Answer them. When it has
enough, it shows the change split into tasks (each one a thin slice you can build in one session) and waits for your
yes. Then it writes the change into `plans/openspec/changes/add-order-export/`: a proposal, the requirements with
their scenarios, and `tasks.md`.

## 3. Build the first task

```text
/lets:build add-order-export
```

The agent proposes a branch name (you choose), then pairs with you on task 1: it explains what to write and why, you
write it, and it checks what you wrote. With test-first, it writes a failing test first and shows it fail. At the end
it shows the output that proves the task works and drafts the commit message. You commit.

If you're using Claude Code's status line, it now reads:

```text
add-order-export ●◉○ › Filter handling   ✎ pair
```

## 4. The rest of the tasks, and review

Build the next task with `/lets:build add-order-export`. Start a fresh session for each task: it keeps the agent's
attention on the task in hand.

When a task modifies something an earlier task depends on, the agent says so and suggests a review first:

```text
/lets:review add-order-export
```

It runs the repo's quick check, reviews against your standards and the change's requirements, and takes a hard look
at the riskiest decisions. It reports one table; "must fix" means something is wrong, not a matter of taste. Fix what
needs fixing, then carry on. The walkthrough offers a review too, if one is due.

## 5. The walkthrough

After the last task:

```text
/lets:walkthrough add-order-export
```

The agent explains the change in the order the code runs, then asks you up to five questions about the decisions and
risks in it. When you've understood it all, record it yourself, in the terminal:

```bash
lets walkthrough complete
```

The agent then drafts the pull request description. Open the pull request.

## 6. Before the final approval

When reviewers have nothing more to ask for:

```text
/lets:change-close add-order-export
```

It merges the change's requirements into the living specs (`plans/openspec/specs/`) and archives the change. Commit
and push that to the pull request, so the specs and the code are approved and merged together. Then merge.

With a planning repo instead, skip this: after you merge, LETS notices the next time you use it and closes the change
itself.

## Where next

- Something small and clear? `/lets:patch` skips the planning.
- Something too big for one pull request? See [Plan an epic](how-to/epics.md).
- Want the agent to write the code? `/lets:build <change> --agent`. See [Agent mode](how-to/agent-mode.md).
